
data {
    int<lower=0> NPT; // Number of player/tournaments
    int<lower=0> NG; // Number of games
    int<lower=0> NMG; // Number of mirror-games
    int<lower=0> NM; // Number of non-mirror matchups
    int<lower=0> NMM; // Number of mirror matchups
    int<lower=0> NVG; // Number of non-mirror validation games
    int<lower=0> NVMG; // Number of mirror validation games
    
    int<lower=0, upper=NPT> prev_tournament[NPT]; // Previous tournament for player/tournament
    
    int<lower=0, upper=1> win[NG]; // Did player 1 win game
    int<lower=1, upper=NPT> pt1[NG]; // Player/tournament 1 in game
    int<lower=1, upper=NPT> pt2[NG]; // Player/tournament 2 in game
    int<lower=1, upper=NM> mup[NG]; // Matchup in game
    
    int<lower=0, upper=1> m_win[NMG]; // Did player 1 win mirror-match
    int<lower=1, upper=NPT> m_pt1[NMG]; // Player/tournament 1 in mirror-match
    int<lower=1, upper=NPT> m_pt2[NMG]; // Player/tournament 2 in mirror-match
    int<lower=1, upper=NM> m_mup[NMG]; // Matchup in game
    
    int<lower=1, upper=NPT> v_pt1[NG]; // Player/tournament 1 in game
    int<lower=1, upper=NPT> v_pt2[NG]; // Player/tournament 2 in game
    int<lower=1, upper=NM> v_mup[NG]; // Matchup in game
    
    int<lower=1, upper=NPT> v_m_pt1[NMG]; // Player/tournament 1 in mirror-match
    int<lower=1, upper=NPT> v_m_pt2[NMG]; // Player/tournament 2 in mirror-match
    int<lower=1, upper=NM> v_m_mup[NMG]; // Matchup in game
    
}
parameters {
    vector[NPT] skill_adjust; // Skill change before player/tournament
    vector[NM] mu; // Matchup value
    vector<lower=0>[NM] muv; // Matchup skill multiplier
    vector<lower=0>[NMM] mmv; // Mirror matchup skill multiplier
}
transformed parameters {
    vector[NPT] skill;
    
    for (t in 1:NPT) {
        if (prev_tournament[t] == 0)
            skill[t] = skill_adjust[t];
        else
            skill[t] = skill[prev_tournament[t]] + skill_adjust[t];
    }
    
}
model {
    skill_adjust ~ std_normal();
    mu ~ normal(0, 0.5);
    mmv ~ std_normal();
    muv ~ std_normal();
    
    win ~ bernoulli_logit(muv[mup] .* (skill[pt1] - skill[pt2]) + mu[mup]);
    m_win ~ bernoulli_logit(mmv[m_mup] .* (skill[m_pt1] - skill[m_pt2]));
}
generated quantities{
    vector[NVG] log_lik_v_win;
    vector[NVMG] log_lik_v_m_win;
    log_lik_v_win += bernoulli_norm_lpdf(inv_logit(muv[v_mup] .* (skill[v_pt1] - skill[v_pt2]) + mu[v_mup]));
    log_lik_v_m_win += bernoulli_norm_lpdf(inv_logit(muv[v_m_mup] .* (skill[v_m_pt1] - skill[v_m_pt2]) + mu[v_m_mup]));
}
