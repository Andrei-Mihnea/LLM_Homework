# smart_librarian/api/message_api.py
from flask import Blueprint, request, jsonify,Response
from smart_librarian.utils.auth_guard import current_user
from smart_librarian.utils.message_helper import check_profanity,sanitize_ctx_messages,to_b64
from smart_librarian.models.chat_db import Conversation
import json
from uuid import uuid4
from openai import OpenAI
import tempfile
import os
from smart_librarian.models.book_model import load_summaries, build_vectorstore,get_summary_by_title,titles
import base64
import io
import openai
api_bp = Blueprint("api", __name__, url_prefix="/api")

COOKIE_CONV = "current_conv_id"
summaries = load_summaries()
VECTORSTORE = build_vectorstore(summaries)
GPT_MODEL="gpt-4o-mini"
# print(summaries)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_summary_by_title",
            "description": "Retrieves the FULL summary for the given exact book title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "enum": titles,
                        "description": "Exact title of the book (must match a candidate)."
                    }
                },
                "required": ["title"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
]

def _require_user():
    u = current_user()
    if not u: return None, (jsonify({"error":"unauthorized"}), 401)
    return u, None

@api_bp.get("/list")
def list_convs():
    user, err = _require_user()
    if err: 
        return err
    convs = Conversation.list_conversations(user)
    return jsonify({"conversations": [
        {"id": c["id"], "title": c["title"], "updated_at": str(c["updated_at"])} for c in convs
    ]})

@api_bp.post("/open")
def api_open():
    user, err = _require_user()  
    if err: 
        return err
    conv_id = (request.get_json(silent=True) or {}).get("conv_id")
    if not conv_id:
        return jsonify({"error":"missing_conv_id"}), 400
    conv = Conversation.get_conversation(user, int(conv_id))
    if not conv: return jsonify({"error":"not_found"}), 404
    resp = jsonify({"conv": {
        "id": conv["id"], "title": conv["title"], "messages": conv.get("messages", [])
    }})
    resp.set_cookie(COOKIE_CONV, str(conv["id"]), httponly=True, samesite="Strict")
    return resp

@api_bp.post("/new")
def api_new():
    user, err = _require_user() 
    if err: 
        return err
    cid = Conversation.create_conversation(user, "New chat")
    conv = Conversation.get_conversation(user, cid)
    resp = jsonify({"conv": {"id": conv["id"], "title": conv["title"], "messages": []}})
    resp.set_cookie(COOKIE_CONV, str(cid), httponly=True, samesite="Strict")
    return resp

@api_bp.post("/delete")
def api_delete():
    user, err = _require_user()
    if err: 
        return err
    conv_id = (request.get_json(silent=True) or {}).get("conv_id")
    if not conv_id: return jsonify({"error":"missing_conv_id"}), 400
    Conversation.delete_conversation(user, int(conv_id))
    return jsonify({"ok": True})

@api_bp.post("/send")
def api_send():
    user, err = _require_user()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()
    if not user_msg:
        return jsonify({"error": "empty_message"}), 400

    conv_id = data.get("conv_id") or request.cookies.get(COOKIE_CONV) or Conversation.create_conversation(user, "New chat")
    conv_id = int(conv_id)
    conv = Conversation.get_conversation(user, conv_id) or Conversation.get_conversation(
        user, Conversation.create_conversation(user, "New chat")
    )

    # --- PROFANITY: show but don't persist ---
    if check_profanity(client, user_msg) is True:
        warning = ("Inappropriate language was detected. This message was flagged and you won't get a reply for it. "
                "Please use an appropriate manner")
        resp_json = jsonify({
            "ok": True,
            "conv": {"id": conv_id, "title": conv["title"]},
            "messages": conv.get("messages", []),  # DB-backed; unchanged
            # NEW: UI-only hints
            "profanity_warning": warning,
            "ephemeral_user_message": user_msg
        })
        resp_json.set_cookie(COOKIE_CONV, str(conv_id), httponly=True, samesite="Strict")
        return resp_json

    
    if not conv.get("messages"):
        Conversation.set_title(user, conv_id, user_msg[:60])
    Conversation.add_message(user, conv_id, "user", user_msg)
    msgs = conv.get("messages", [])
    
    
    # === RAG: top-k candidați + scoruri ===
    docs = VECTORSTORE.similarity_search_with_relevance_scores(user_msg, k=3)
    candidates_text = "\n\n".join(
        f"- id: {i+1}\n  title: {d.metadata.get('title', 'Untitled')}\n  relevance: {score:.2f}"
        for i, (d, score) in enumerate(docs)
    )
    # print(msgs)
    # === Prompt assistant (reguli clare) ===
    allowed_titles = ", ".join(titles)  # the enum you already pass to the tool
    system_prompt = ( f'''
You are a friendly Library Assistant AI with a warm, encouraging tone.

You MUST ONLY recommend books that appear in this candidate list (the library):
{candidates_text}

Each item looks like:
## Title: <Exact Title>
<Short summary ending with: "Themes: ...">

NON-NEGOTIABLE RULES
1) Library-only: Never mention books outside {candidates_text}. If nothing matches, say kindly that it’s not in the library.
2) No hallucinations: Do NOT invent or paraphrase summaries, titles, authors, or themes.
3) Auto-fetch summaries: Any time you present or even mention a book, you MUST immediately call the tool `fetch_summary` with its exact canonical title and then display the tool’s returned summary verbatim. Do not ask the user first.
4) Robust title matching BEFORE you claim “not found”:
   - Normalize the user’s title query by: lowercase, trim spaces, collapse multiple spaces, and remove punctuation/quotes (e.g., smart quotes, commas, periods, dashes, apostrophes).
   - Normalize all library titles the same way.
   - If a normalized exact match exists, treat it as found and fetch its summary. DO NOT propose alternatives.
   - Only if no normalized exact match is found may you treat it as not in the library.
5) Theme matching:
   - If the user asks by theme/keywords (e.g., “dystopian”, “friendship”), select up to 3 titles whose summaries’ “Themes:” line overlaps best.
   - For each selected title, ALWAYS fetch and display the verbatim summary.
6) Output policy:
   - Present a warm, concise opener (one sentence max). No more than one emoji, and only if it fits the user’s vibe.
   - For each title you output: **Title** — [VERBATIM summary returned by `fetch_summary`].
   - If no matches: say so kindly, then offer up to 3 closest thematic alternatives, each with a verbatim fetched summary.
7) Safety rails against paraphrasing:
   - Never summarize in your own words.
   - Never rephrase or “clarify” the tool output.
   - If the tool returns nothing, do NOT print a guess or alternative text for that title; omit the title or retry with the canonical one.

Be strict about sources. Friendly tone, but accuracy first.
 ''' )





    ctx_messages = [
        {"role": "system", "content": system_prompt},
    ]
    msgs = sanitize_ctx_messages(msgs)
    
    for m in msgs:
        ctx_messages.append(m)
    ctx_messages.append( {"role": "user", "content": user_msg})

    ai = client.chat.completions.create(
        model=GPT_MODEL,
        messages=ctx_messages,
        temperature=0.6,
        tools=tools,
        tool_choice="auto"

    )
    assistant_response = ""
    assistant_response_raw = ai.choices[0].message
    text_response = assistant_response_raw.content or ""
    
    # print(tool_raw_reply.content)
    print(assistant_response_raw)
    # print(first.output)
    tool_calls = assistant_response_raw.tool_calls or []
    summary_text=""
    if tool_calls == []:
        print("tool_calls este gol")
    for call in tool_calls:
        print(f"Function called {call.function.name}")
        if call.type == "function" and call.function and call.function.name == "get_summary_by_title":
            print(f"Function called {call.function.name}")
             # arguments e un string JSON
            raw_args = call.function.arguments or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
            title = (args.get("title") or "").strip()
            if title:
                summary_text = get_summary_by_title(title)
                text_response += f"\n\n „{title}”\n{summary_text}"
            break
    

    tts_payload = None
    tts_requested = bool(data.get("tts_enable"))
    print(f"tts_requested = {tts_requested}", flush=True)
    
    
    tts_text = (summary_text.strip() or (text_response or "").strip())
    MAX_TTS_CHARS = 1800
    tts_text = tts_text[:MAX_TTS_CHARS]

    image_payload = None
    image_generation_requested = bool(data.get("image_enable"))
    image_generation_text = (text_response or "").strip()

    if image_generation_requested and image_generation_text and summary_text:
        try:
            # Use the Images API to get a base64 PNG (compact & predictable)
            img = client.images.generate(
                model="gpt-image-1",
                prompt=f"Generate an image where you expose the action from this summary(with the characters or the action mentioned):\n{image_generation_text}\nHard rules!!:\nDon't add text except for the title",
                size="1024x1024"
            )
            image_b64 = img.data[0].b64_json  # <-- base64 PNG string

            # Embed into the assistant content so it persists in history
            text_response += f"<image type=\"image/png\">{image_b64}</image>"
        except Exception as e:
            # Optional: add a small notice in the text; or ignore silently
            text_response += "\n\n[Image generation failed]"
        
    assistant_response += text_response

    if tts_requested and tts_text:
        resp = client.audio.speech.create(
            model=GPT_MODEL+"-tts",
            voice="alloy",
            input=tts_text,
        )

        audio_bytes = resp.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        assistant_response += f"<audio>{audio_b64}</audio>"

        tts_payload = {
        "audio_b64": audio_b64,
        "mime": "audio/mpeg",
        "voice": "alloy",
        }
    
    Conversation.add_message(user, conv_id, "assistant", assistant_response)

    conv = Conversation.get_conversation(user, conv_id)
    resp_json = jsonify({
        "ok": True,
        "conv": {"id": conv_id, "title": conv["title"]},
        "messages": conv.get("messages", []),
        "assistant_reply": assistant_response,
        "tts":tts_payload
    })
    resp_json.set_cookie(COOKIE_CONV, str(conv_id), httponly=True, samesite="Strict")
    return resp_json

@api_bp.post("/stt")
def stt():
    f = request.files.get("audio")
    if not f:
        return jsonify({"error": "no_audio"}), 400

    language = request.form.get("language")
    prompt   = request.form.get("prompt")

    args = {
        "model": GPT_MODEL + "-transcribe",  # e.g. gpt-4o-mini-transcribe
        "file": (f.filename, f.stream, f.mimetype or "application/octet-stream"),
    }
    if language: args["language"] = language
    if prompt:   args["prompt"]   = prompt

    try:
        tr = client.audio.transcriptions.create(**args)
    except openai.BadRequestError as e:
        msg = str(e)
        # Detect the short-audio case and return a helpful response
        if "audio duration" in msg and "minimum" in msg:
            return jsonify({
                "error": "too_short",
                "message": "Recording too short. Please record at least 0.3–0.5 seconds."
            }), 422
        # Bubble up any other request issue
        return jsonify({"error": "bad_request", "message": msg}), 400

    text = getattr(tr, "text", None) or (tr.get("text") if isinstance(tr, dict) else None)
    return jsonify({"text": text or ""})
