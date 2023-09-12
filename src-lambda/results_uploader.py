import gspread
import os
from tempfile import NamedTemporaryFile
import sys
import json
import pprint
import logging

creds_file = NamedTemporaryFile()
creds_file.write(os.environ["GOOGLE_CREDS"].encode("utf8"))
creds_file.flush()

gc = gspread.service_account(filename=creds_file.name)
sh = gc.open_by_key("1DMq27BcMST27m4A_sws-CYs4PI41B7T8G28bqSyFSr8")
wksh = sh.worksheet("Results")


# Example game:
# {
#     "threadId": "_",
#     "timestamp": "2455.518",
#     "gameType": "FriendMatchOnline",
#     "p0Location": "Remote",
#     "p0Name": "Hobusu",
#     "p0Char": "Lum",
#     "p0Gem": "Black",
#     "result": "wins",
#     "p1Location": "Local",
#     "p1Name": "vengefulpickle",
#     "p1Char": "DragonMidori",
#     "p1Gem": "Green",
#     "realTime": "2023-09-09T03:28:20.804Z",
#     "zeroTime": 1694227645286,
#     "rawLine": "[_ 2455.518] FriendMatchOnline Game over: Remote P0 [Hobusu] Lum-Black wins vs Local P1 [vengefulpickle] DragonMidori-Green"
# }

# Message body should contain a list of games under the "games" key

# Example cmdline
# '{"httpMethod": "POST", "body": "{\"games\": [{\"threadId\": \"_\",\"timestamp\": \"2455.518\",\"gameType\": \"FriendMatchOnline\",\"p0Location\": \"Remote\",\"p0Name\": \"Hobusu\",\"p0Char\": \"Lum\",\"p0Gem\": \"Black\",\"result\": \"wins\",\"p1Location\": \"Local\",\"p1Name\": \"vengefulpickle\",\"p1Char\": \"DragonMidori\",\"p1Gem\": \"Green\",\"realTime\": \"2023-09-09T03:28:20.804Z\",\"zeroTime\": 1694227645286,\"rawLine\":\"[_ 2455.518] FriendMatchOnline Game over: Remote P0 [Hobusu] Lum-Black wins vs Local P1 [vengefulpickle] DragonMidori-Green\"}]}"}'


def format_response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Origin": "https://vengefulpickle.com",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "isBase64Encoded": False,
        "body": json.dumps(body),
    }


def handle_result(event, context):
    if event["httpMethod"] == "OPTIONS":
        return format_response(200, {})
    if event["httpMethod"] != "POST":
        return format_response(
            405, {"message": "Only POST AND OPTIONS are accepted methods"}
        )

    print(event["body"])
    body_json = json.loads(event["body"])

    if "games" in body_json:
        games = body_json["games"]
    else:
        games = [body_json]

    results = []
    rows = []
    for game in games:
        try:
            existing_cell = wksh.find(game["rawLine"], in_column=9)
            if existing_cell:
                results.append(
                    {
                        "rawLine": game["rawLine"],
                        "result": "skipped",
                        "message": "Game already exists",
                    }
                )
            else:
                rows.append(
                    [
                        game["realTime"],
                        game["p0Name"],
                        game["p0Char"],
                        game["p0Gem"],
                        game["p1Name"],
                        game["p1Char"],
                        game["p1Gem"],
                        "P1" if game["result"] == "wins" else "P2",
                        game["rawLine"],
                    ]
                )
                results.append(
                    {
                        "rawLine": game["rawLine"],
                        "result": "uploaded",
                        "message": "Game uploaded",
                    }
                )
        except:
            logging.exception("Failed to parse line")
            results.append(
                {
                    "rawLine": game["rawLine"],
                    "result": "failed",
                    "message": "Game parsing failed",
                }
            )

    dates = wksh.col_values(1)
    next_row = len(dates) + 1
    wksh.update(range_name=f"A{next_row}:I{next_row + len(rows)-1}", values=rows)

    return format_response(200, {"results": results})


if __name__ == "__main__":
    response = handle_result(json.loads(sys.argv[1]), json.loads(sys.argv[2]))

    pprint.pprint(response)
    sys.exit(response["statusCode"] == 200)
