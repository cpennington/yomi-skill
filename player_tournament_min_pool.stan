data {
    int<lower=0> NPT; // Number of player/tournaments
    int<lower=0> NG; // Number of games
    int<lower=0> NM; // Number of matchups
    int<lower=0> NP; // Number of players
    int<lower=0> NC; // Number of characters

    int<lower=1, upper=NP> tp[NPT]; // Player n game

    int<lower=0, upper=1> win[NG]; // Did player 1 win game
    int<lower=1, upper=NPT> pt1[NG]; // Player/tournament 1 in game
    int<lower=1, upper=NPT> pt2[NG]; // Player/tournament 2 in game
    int<lower=1, upper=NM> mup[NG]; // Matchup in game
    vector<lower=0, upper=1>[NG] non_mirror; // Is this a mirror matchup: 0 = mirror
}
parameters {
    vector[NPT] skill_in_tournament; // Skill for a specific player/tournament
    vector[NM] mu; // Matchup value
    vector[NP] global_player_skill; //
    real<lower=0> tournament_variance; // How much variance is there around a player skill per tournament
    real<lower=0> player_variance;
}
transformed parameters {
    vector[NP] player_skill;
    vector[NPT] skill;
    vector[NG] win_chance;

    player_skill = global_player_skill * player_variance;
    skill = player_skill[tp] + skill_in_tournament * tournament_variance;
    win_chance = (skill[pt1] - skill[pt2]) +  non_mirror .* mu[mup];
}
model {
    global_player_skill ~ std_normal();
    skill_in_tournament ~ std_normal();
    mu ~ normal(0, 0.5);

    win ~ bernoulli_logit(win_chance);
}
generated quantities{
    vector[NG] log_lik;
    vector[NG] win_hat;

    for (n in 1:NG) {
        log_lik[n] = bernoulli_logit_lpmf(win[n] | win_chance[n]);
        win_hat[n] = bernoulli_logit_rng(win_chance[n] );
    }
}
