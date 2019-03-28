data {
    int<lower=0> NG; // Number of games
    int<lower=0> NM; // Number of matchups
    int<lower=0> NP; // Number of players
    int<lower=0> NC; // Number of characters
    int<lower=0> NMV; // Number of matchup versions

    int<lower=1, upper=NM> mu_for_v[NMV]; // Which matchup is this a version of

    int<lower=0, upper=1> win[NG]; // Did player 1 win game
    int<lower=1, upper=NMV> vmup[NG]; // Matchup version in game
    vector<lower=0, upper=1>[NG] non_mirror; // Is this a mirror matchup: 0 = mirror
    int<lower=1, upper=NC> char1[NG]; // Character 1 in game
    int<lower=1, upper=NC> char2[NG]; // Character 2 in game
    int<lower=1, upper=NP> player1[NG]; // Player 1 in game
    int<lower=1, upper=NP> player2[NG]; // Player 1 in game
    vector[NG] elo_logit; // Player 1 ELO-based logit win chance
}
parameters {
    vector[NM] mu_mean; // Matchup value
    vector<lower=0>[NM] mu_std; // Matchup value
    vector[NMV] vmu_raw; // Matchup version value
    vector<upper=0>[NP] char_skill[NC]; // Player skill at character
    real elo_logit_scale; // elo_logit scale
}
transformed parameters {
    vector[NG] player_char_skill1;
    vector[NG] player_char_skill2;
    vector[NG] win_chance_logit;
    vector[NMV] vmu;

    for (n in 1:NG) {
        player_char_skill1[n] = char_skill[char1[n], player1[n]];
        player_char_skill2[n] = char_skill[char2[n], player2[n]];
    }

    vmu = mu_mean[mu_for_v] + vmu_raw .* mu_std[mu_for_v];

    win_chance_logit = (player_char_skill1 - player_char_skill2) + non_mirror .* vmu[vmup] + elo_logit_scale * elo_logit;
}
model {
    for (n in 1:NC) {
        char_skill[n] ~ std_normal();
    }
    mu_mean ~ normal(0, 0.2);
    mu_std ~ normal(0, 0.5);
    vmu_raw ~ std_normal();
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
