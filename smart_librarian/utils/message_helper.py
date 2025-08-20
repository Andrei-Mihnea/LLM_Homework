def check_profanity(client,message:str) -> bool:
    resp = client.moderations.create(
        model="omni-moderation-latest",
        input=message
    )

    flagged = resp.results[0].flagged
    categories = resp.results[0].categories

    if flagged:
        print("⚠️ Message flagged:", categories)
    return flagged