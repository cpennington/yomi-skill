data {
    int<lower=0> NTG; // Number of training games
    int<lower=0> NVG; // Number of validation games
    int<lower=0> NM; // Number of matchups
    int<lower=0> NP; // Number of players
    int<lower=0> NC; // Number of characters
    
    int<lower=0, upper=1> winT[NTG]; // Did player 1 win game
    int<lower=1, upper=NM> mupT[NTG]; // Matchup in game
    vector<lower=0, upper=1>[NTG] non_mirrorT; // Is this a mirror matchup: 0 = mirror
    int<lower=1, upper=NC> char1T[NTG]; // Character 1 in game
    int<lower=1, upper=NC> char2T[NTG]; // Character 2 in game
    int<lower=1, upper=NP> player1T[NTG]; // Player 1 in game
    int<lower=1, upper=NP> player2T[NTG]; // Player 2 in game
    vector[NTG] elo_logitT; // Player 1 ELO-based logit win chance

    int<lower=0, upper=1> winV[NVG]; // Did player 1 win game
    int<lower=1, upper=NM> mupV[NVG]; // Matchup in game
    vector<lower=0, upper=1>[NVG] non_mirrorV; // Is this a mirror matchup: 0 = mirror
    int<lower=1, upper=NC> char1V[NVG]; // Character 1 in game
    int<lower=1, upper=NC> char2V[NVG]; // Character 2 in game
    int<lower=1, upper=NP> player1V[NVG]; // Player 1 in game
    int<lower=1, upper=NP> player2V[NVG]; // Player 2 in game
    vector[NVG] elo_logitV; // Player 1 ELO-based logit win chance
}
parameters { 
    vector[NM] mu; // Matchup value
    vector<upper=0>[NP] char_skill[NC]; // Player skill at character
    real elo_logit_scale; // elo_logit scale
}
transformed parameters {
    vector[NTG] win_chance_logit;
    // win_chance_logit = (char_skill[char1, player1] - char_skill[char2, player2]) + non_mirror .* mu[mup] + elo_logit_scale * elo_logit;

    for (n in 1:NTG) {
        win_chance_logit[n] = 
            char_skill[char1T[n], player1T[n]] -
            char_skill[char2T[n], player2T[n]] +
            non_mirrorT[n] * mu[mupT[n]] +
            elo_logit_scale * elo_logitT[n];
    }
}
model {
    for (n in 1:NC) {
        char_skill[n] ~ std_normal();
    }
    mu ~ normal(0, 0.5);
    elo_logit_scale ~ std_normal();

    winT ~ bernoulli_logit(win_chance_logit);
}
generated quantities{
    vector[NTG] log_lik;
    vector[NTG] win_hat;

    for (n in 1:NTG) {
        log_lik[n] = bernoulli_logit_lpmf(winT[n] | win_chance_logit[n]);
        win_hat[n] = bernoulli_logit_rng(win_chance_logit[n]);
    }
}
