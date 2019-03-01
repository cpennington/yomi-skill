data {
    int<lower=0> NG; // Number of games
    int<lower=0> NM; // Number of matchups
    int<lower=0> NP; // Number of players
    int<lower=0> NC; // Number of characters

    int<lower=0, upper=1> win[NG]; // Did player 1 win game
    int<lower=1, upper=NM> mup[NG]; // Matchup in game
    vector<lower=0, upper=1>[NG] non_mirror; // Is this a mirror matchup: 0 = mirror
    int<lower=1, upper=NC> char1[NG]; // Character 1 in game
    int<lower=1, upper=NC> char2[NG]; // Character 2 in game
    int<lower=1, upper=NP> player1[NG]; // Player 1 in game
    int<lower=1, upper=NP> player2[NG]; // Player 1 in game
    vector[NG] elo_logit; // Player 1 ELO-based logit win chance
    vector[NG] obs_weights;
}
parameters {
    vector[NM] mu; // Matchup value
    vector<upper=0>[NP] char_skill_raw[NC]; // Player skill at character
    vector<upper=0>[NC] char_skill_mean; // Average player skill at character
    vector<lower=0>[NC] char_skill_variance; // Player skill variance per character
    real elo_logit_scale; // elo_logit scale
}
transformed parameters {
    vector[NG] player_char_skill1;
    vector[NG] player_char_skill2;
    vector[NG] win_chance_logit;
    vector<upper=0>[NP] char_skill[NC]; // Player skill at character

    for (c in 1:NC) {
        char_skill[c] = char_skill_mean[c] + char_skill_raw[c] * char_skill_variance[c];
    }
    for (n in 1:NG) {
        player_char_skill1[n] = char_skill[char1[n], player1[n]];
        player_char_skill2[n] = char_skill[char2[n], player2[n]];
    }
    win_chance_logit = (player_char_skill1 - player_char_skill2) + non_mirror .* mu[mup] + elo_logit_scale * elo_logit;
}
model {
    for (n in 1:NC) {
        char_skill_raw[n] ~ std_normal();
    }
    mu ~ normal(0, 0.5);
    elo_logit_scale ~ std_normal();
    char_skill_mean ~ uniform(-4, 0);
    char_skill_variance ~ normal(0, 3);

    for (n in 1:NG) {
        target += bernoulli_logit_lpmf(win[n] | win_chance_logit[n]) * obs_weights[n];
    }
}
generated quantities{
    vector[NG] log_lik;
    vector[NG] win_hat;

    for (n in 1:NG) {
        log_lik[n] = bernoulli_logit_lpmf(win[n] | win_chance_logit[n]) * obs_weights[n];
        win_hat[n] = bernoulli_logit_rng(win_chance_logit[n]);
    }
}
