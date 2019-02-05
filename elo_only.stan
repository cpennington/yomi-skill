data {
    int<lower=0> NG; // Number of games
    int<lower=0> NM; // Number of matchups

    int<lower=0, upper=1> win[NG]; // Did player 1 win game
    int<lower=1, upper=NM> mup[NG]; // Matchup in game
    vector<lower=0, upper=1>[NG] non_mirror; // Is this a mirror matchup: 0 = mirror
    vector[NG] elo_logit; // Player 1 ELO-based logit win chance
}
parameters {
    vector[NM] mu; // Matchup value
    real elo_logit_scale; // elo_logit scale
}
transformed parameters {
    vector[NG] win_chance_logit;

    win_chance_logit = non_mirror .* mu[mup] + elo_logit_scale * elo_logit;
}
model {
    mu ~ normal(0, 0.5);
    elo_logit_scale ~ std_normal();

    win ~ bernoulli_logit(win_chance_logit);
}
generated quantities{
    vector[NG] log_lik;
    vector[NG] win_hat;

    for (n in 1:NG) {
        log_lik[n] = bernoulli_logit_lpmf(win[n] | win_chance_logit[n]);
        win_hat[n] = bernoulli_logit_rng(win_chance_logit[n]);
    }
}
