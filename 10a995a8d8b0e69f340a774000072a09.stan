data {
    int<lower=0> NPT; // Number of player/tournaments
    int<lower=0> NG; // Number of games
    int<lower=0> NM; // Number of matchups
    int<lower=0> NP; // Number of players

    int<lower=0, upper=NPT> prev_tournament[NPT]; // Previous tournament for player/tournament

    int<lower=1, upper=NP> tp[NPT]; // Player n game

    int<lower=0, upper=1> win[NG]; // Did player 1 win game
    int<lower=1, upper=NPT> pt1[NG]; // Player/tournament 1 in game
    int<lower=1, upper=NPT> pt2[NG]; // Player/tournament 2 in game
    int<lower=1, upper=NM> mup[NG]; // Matchup in game
    vector<lower=0, upper=1>[NG] non_mirror; // Is this a mirror matchup: 0 = mirror

}
parameters {
    vector[NPT] skill; // Skill change before player/tournament
    vector[NM] mu; // Matchup value
    vector<lower=0>[NM] muv; // Matchup skill multiplier
    real baseline_skill; // Average baseline player skill
    vector[NP] player_skill; //
}
model {
    baseline_skill ~ std_normal();
    player_skill ~ normal(0, baseline_skill);
    skill ~ normal(0, player_skill[tp]);
    mu ~ normal(0, 0.5);
    muv ~ std_normal();

    win ~ bernoulli_logit(muv[mup] .* (skill[pt1] - skill[pt2]) +  non_mirror .* mu[mup]);
}
generated quantities{
    vector[NG] log_lik;
    vector[NG] win_hat;

    for (n in 1:NG) {
        log_lik[n] = bernoulli_logit_lpmf(win[n] | muv[mup[n]] * (skill[pt1[n]] - skill[pt2[n]]) + non_mirror[n] * mu[mup[n]]);
        win_hat[n] = bernoulli_logit_rng( muv[mup[n]] * (skill[pt1[n]] - skill[pt2[n]]) + non_mirror[n] * mu[mup[n]]);
    }
}
