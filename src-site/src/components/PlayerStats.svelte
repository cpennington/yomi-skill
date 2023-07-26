<script>
    //   if (player) {
    //     document.getElementById("p1-name").textContent = player;
    //     document.getElementById("p1-elo").textContent = Math.round(
    //       playerSkill[player].elo
    //     );
    //     document.getElementById("p1-games").textContent =
    //       playerSkill[player].gamesPlayed;
    //   }
    //   if (opponent) {
    //     againstCfg.display = "none";
    //     document.getElementById("p2-name").textContent = opponent;
    //     document.getElementById("p2-elo").textContent = Math.round(
    //       playerSkill[opponent].elo
    //     );
    //     document.getElementById("p2-games").textContent =
    //       playerSkill[opponent].gamesPlayed;
    //   }
</script>

<table id="player-stats" class="table table-hover table-sm mt-2">
    <thead>
        <tr>
            <th>Player</th>
            <th>Elo</th>
            <th>Games recorded</th>
        </tr>
    </thead>
    <tbody>
        <tr id="p1-stats">
            <td id="p1-name" />
            <td id="p1-elo" />
            <td id="p1-games" />
        </tr>
        <tr id="p2-stats">
            <td id="p2-name" />
            <td id="p2-elo" />
            <td id="p2-games" />
        </tr>
    </tbody>
</table>
