<script lang="ts">
    import loadingSVG from "../assets/loading.svg";
    import { get, set } from "idb-keyval";
    import { showDirectoryPicker } from "file-system-access";

    let uploading = false;
    let lastMessage: string | undefined = undefined;

    function toMillis(seconds: number): number {
        return seconds * 1000;
    }

    async function processLogFiles(
        fileHandles: Promise<FileSystemFileHandle>[]
    ) {
        if (!uploading) {
            return;
        }
        const handles = await Promise.all(fileHandles);

        const games = [];
        const now = new Date();

        for (const handle of handles) {
            const file = await handle.getFile();
            const startTime =
                /\[(?<threadId>.) (?<timestamp>[^\]]*)\] Yomi2 Start: (?<version>.*) at localtime (?<localTime>[^,]*), UTC (?<utcTime>.*)/;

            const matchComplete =
                /\[(?<threadId>.) (?<timestamp>[^\]]*)\] (?<gameType>[^ ]*) Game over: (?<p0Location>Remote|Local) P0 \[(?<p0Name>[^\]]*)\] (?<p0Char>[^-]*)-(?<p0Gem>[^ ]*) (?<result>[^ ]*) vs (?<p1Location>Remote|Local) P1 \[(?<p1Name>[^\]]*)\] (?<p1Char>[^-]*)-(?<p1Gem>\S*)/;

            let zeroTime = null;
            for (const line of (await file.text()).split("\n") as string[]) {
                const rawLine = line.trim();
                const lastProcessed: Date | undefined = await get(rawLine);
                const startTimeMatch = startTime.exec(line);
                const matchCompleteMatch = matchComplete.exec(line);

                if (startTimeMatch) {
                    const startMillis = new Date(
                        startTimeMatch.groups!.utcTime.replace(" ", "T")
                    ).valueOf();
                    const offsetMillis = toMillis(
                        new Number(startTimeMatch.groups!.timestamp).valueOf()
                    );
                    zeroTime = startMillis - offsetMillis;
                }
                if (matchCompleteMatch) {
                    if (
                        lastProcessed &&
                        now.getTime() - lastProcessed.getTime() <
                            toMillis(4 * 60 * 60)
                    ) {
                        continue;
                    }

                    const match = {
                        ...matchCompleteMatch.groups,
                        realTime: new Date(
                            toMillis(
                                new Number(
                                    matchCompleteMatch.groups!.timestamp
                                ).valueOf()
                            ) + zeroTime!
                        ),
                        zeroTime,
                        rawLine,
                    };
                    games.push(match);
                }
            }
        }

        if (games.length > 0) {
            const response = await fetch(
                "https://yomi-2-results-uploader.vengefulpickle.com",
                {
                    body: JSON.stringify({ games }),
                    headers: { "Content-Type": "application/json" },
                    method: "POST",
                }
            );
            let successes = 0;
            let failures = 0;
            for (const { rawLine, result, message } of (await response.json())
                .results) {
                if (result === "uploaded") {
                    set(rawLine, now);
                    successes += 1;
                } else if (result === "failed") {
                    failures += 1;
                    console.warn({ rawLine, result, message });
                } else if (result === "skipped") {
                    set(rawLine, now);
                }
            }
            if (response.status >= 400) {
                lastMessage =
                    "Error uploading results, please ping @vengefulpickle on the Sirlin Games discord.";
            } else {
                if (failures > 0) {
                    lastMessage = `${now}: ${successes} games successfully uploaded, ${failures} games failed to uploade`;
                } else {
                    lastMessage = `${now}: ${successes} games successfully uploaded`;
                }
            }
            console.log({ response, lastMessage });
        } else {
            lastMessage = `${now}: No new games found`;
        }
        setTimeout(() => processLogFiles(fileHandles), toMillis(300));
    }

    async function watchLogs() {
        uploading = true;

        const handle = await showDirectoryPicker({});
        const playerLog = handle.getFileHandle("Player.log");
        const oldPlayerLog = handle.getFileHandle("Player-prev.log");
        processLogFiles([playerLog, oldPlayerLog]);
    }
</script>

<div class="row col-12">
    <p class="col-12 mt-4">
        If you'd like to improve the matchup chart, upload your match results by
        clicking the Upload button below, and navigating to the Yomi 2 log files
        directory:
    </p>
    <ul class="list-disc pl-10">
        <li>
            Windows: <pre
                class="inline">%USERPROFILE%\AppData\LocalLow\Sirlin Games\Yomi 2</pre>
        </li>
        <li>
            Mac: <pre class="inline">~/Library/Logs/Sirlin Games/Yomi 2</pre>
        </li>
        <li>
            Linux: <pre
                class="inline">~/.config/unity3d/Sirlin Games/Yomi 2</pre>
        </li>
    </ul>
    <p>
        <em>N.B.</em> The directory may appear empty in the directory picker, but
        you should be able to "Select Folder" to trigger the upload.
    </p>
    {#if uploading}
        <button
            class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded"
            on:click={() => {
                uploading = false;
            }}>Uploading!</button
        >
        <img
            class="h-5 animate-spin inline"
            src={loadingSVG.src}
            alt="Uploading..."
        />
        {#if lastMessage}<pre>{lastMessage}</pre>{/if}
    {:else}
        <button
            class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            on:click={watchLogs}>Upload!</button
        >
    {/if}
</div>
