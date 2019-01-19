
data {
    int<lower=0> NPT; // Number of player/tournaments
    int<lower=0> NG; // Number of games
    int<lower=0> NMG; // Number of mirror-games
    int<lower=0> NM; // Number of non-mirror matchups
    int<lower=0> NMM; // Number of mirror matchups
    
    int<lower=0, upper=NPT> prev_tournament[NPT]; // Previous tournament for player/tournament
    
    int<lower=0, upper=1> win[NG]; // Did player 1 win game
    int<lower=1, upper=NPT> pt1[NG]; // Player/tournament 1 in game
    int<lower=1, upper=NPT> pt2[NG]; // Player/tournament 2 in game
    int<lower=1, upper=NM> mup[NG]; // Matchup in game
    
    int<lower=0, upper=1> m_win[NMG]; // Did player 1 win mirror-match
    int<lower=1, upper=NPT> m_pt1[NMG]; // Player/tournament 1 in mirror-match
    int<lower=1, upper=NPT> m_pt2[NMG]; // Player/tournament 2 in mirror-match
    
}
parameters {
    vector[NPT] skill_adjust; // Skill change before player/tournament
    vector[NM] mu; // Matchup value
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
    
    win ~ bernoulli_logit(skill[pt1] - skill[pt2] + mu[mup]);
    m_win ~ bernoulli_logit(skill[m_pt1] - skill[m_pt2]);
}
