data {
    int<lower=0> NPT; // Number of player/tournaments
    int<lower=0> NG; // Number of games
    int<lower=0> NM; // Number of matchups
    int<lower=0> NP; // Number of players
    int<lower=0> NC; // Number of characters

    int<lower=0, upper=NPT> prev_tournament[NPT]; // Previous tournament for player/tournament

    int<lower=0, upper=1> win[NG]; // Did player 1 win game
    int<lower=1, upper=NPT> pt1[NG]; // Player/tournament 1 in game
    int<lower=1, upper=NPT> pt2[NG]; // Player/tournament 2 in game
    int<lower=1, upper=NM> mup[NG]; // Matchup in game
    vector<lower=0, upper=1>[NG] non_mirror; // Is this a mirror matchup: 0 = mirror
    int<lower=1, upper=NC> char1[NG]; // Character 1 in game
    int<lower=1, upper=NC> char2[NG]; // Character 2 in game
    int<lower=1, upper=NP> player1[NG]; // Player 1 in game
    int<lower=1, upper=NP> player2[NG]; // Player 1 in game
}
parameters {
    vector[NPT] skill_adjust; // Skill change before player/tournament
    vector[NM] mu; // Matchup value
    vector[NP] char_skill[NC]; // Player skill at character
}
transformed parameters {
    vector[NPT] skill;
    vector[NG] player_char_skill1;
    vector[NG] player_char_skill2;

    for (t in 1:NPT) {
        if (prev_tournament[t] == 0)
            skill[t] = skill_adjust[t];
        else
            skill[t] = skill[prev_tournament[t]] + skill_adjust[t];
    }

    for (n in 1:NG) {
        player_char_skill1[n] = char_skill[char1[n], player1[n]];
        player_char_skill2[n] = char_skill[char2[n], player2[n]];
    }

}
model {
    skill_adjust ~ std_normal();
    mu ~ normal(0, 0.5);

    win ~ bernoulli_logit((skill[pt1] + player_char_skill1 - skill[pt2] - player_char_skill2) +  non_mirror .* mu[mup]);
}
generated quantities{
    vector[NG] log_lik;
    vector[NG] win_hat;

    for (n in 1:NG) {
        log_lik[n] = bernoulli_logit_lpmf(win[n] | (skill[pt1[n]] + player_char_skill1[n] - skill[pt2[n]] - player_char_skill2[n]) + non_mirror[n] * mu[mup[n]]);
        win_hat[n] = bernoulli_logit_rng((skill[pt1[n]] + player_char_skill1[n] - skill[pt2[n]] - player_char_skill2[n]) + non_mirror[n] * mu[mup[n]]);
    }
}
