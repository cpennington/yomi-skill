import gspread
import os
from tempfile import NamedTemporaryFile
import sys
import json
import pprint

creds_file = NamedTemporaryFile()
creds_file.write(os.environ["GOOGLE_CREDS"].encode("utf8"))
creds_file.flush()

gc = gspread.service_account(filename=creds_file.name)
sh = gc.open_by_key("1DMq27BcMST27m4A_sws-CYs4PI41B7T8G28bqSyFSr8")
wksh = sh.worksheet("Results")


# Example body:
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

# Example cmdline
# '{"body": "{\"threadId\": \"_\",\"timestamp\": \"2455.518\",\"gameType\": \"FriendMatchOnline\",\"p0Location\": \"Remote\",\"p0Name\": \"Hobusu\",\"p0Char\": \"Lum\",\"p0Gem\": \"Black\",\"result\": \"wins\",\"p1Location\": \"Local\",\"p1Name\": \"vengefulpickle\",\"p1Char\": \"DragonMidori\",\"p1Gem\": \"Green\",\"realTime\": \"2023-09-09T03:28:20.804Z\",\"zeroTime\": 1694227645286,\"rawLine\":\"[_ 2455.518] FriendMatchOnline Game over: Remote P0 [Hobusu] Lum-Black wins vs Local P1 [vengefulpickle] DragonMidori-Green\"}"}'


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

    body_json = json.loads(event["body"])
    existing_cell = wksh.find(body_json["rawLine"], in_column=9)
    if existing_cell:
        return format_response(200, {"message": "Row already exists"})

    first_empty = wksh.find("", in_column=1)
    next_row = first_empty.row
    wksh.update(
        range_name=f"A{next_row}:I{next_row}",
        values=[
            [
                body_json["realTime"],
                body_json["p0Name"],
                body_json["p0Char"],
                body_json["p0Gem"],
                body_json["p1Name"],
                body_json["p1Char"],
                body_json["p1Gem"],
                "P1" if body_json["result"] == "wins" else "P2",
                body_json["rawLine"],
            ]
        ],
    )

    return format_response(200, {"message": "Row added"})


if __name__ == "__main__":
    response = handle_result(json.loads(sys.argv[1]), json.loads(sys.argv[2]))

    pprint.pprint(response)
    sys.exit(response["statusCode"] == 200)
