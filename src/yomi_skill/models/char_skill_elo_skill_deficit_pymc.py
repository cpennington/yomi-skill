from ..model import elo_logit
from .pymc_model import PyMCModel
import os
from scipy.special import expit
from IPython.core.display import display
from functools import cached_property
import pymc as pm


class CharSkillEloSkillDeficitPyMC(PyMCModel):
    model_name = "char_skill_elo_skill_deficit_pymc"

    @cached_property
    def model(self):
        with pm.Model() as model:
            # data {
            #     int<lower=0> NTG; // Number of training games
            #     int<lower=0> NVG; // Number of validation games
            #     int<lower=0> NM; // Number of matchups
            #     int<lower=0> NP; // Number of players
            #     int<lower=0> NC; // Number of characters

            #     int<lower=0, upper=1> winT[NTG]; // Did player 1 win game
            #     int<lower=1, upper=NM> mupT[NTG]; // Matchup in game
            #     vector<lower=0, upper=1>[NTG] non_mirrorT; // Is this a mirror matchup: 0 = mirror
            #     int<lower=1, upper=NC> char1T[NTG]; // Character 1 in game
            #     int<lower=1, upper=NC> char2T[NTG]; // Character 2 in game
            #     int<lower=1, upper=NP> player1T[NTG]; // Player 1 in game
            #     int<lower=1, upper=NP> player2T[NTG]; // Player 2 in game
            #     vector[NTG] elo_logitT; // Player 1 ELO-based logit win chance

            #     int<lower=0, upper=1> winV[NVG]; // Did player 1 win game
            #     int<lower=1, upper=NM> mupV[NVG]; // Matchup in game
            #     vector<lower=0, upper=1>[NVG] non_mirrorV; // Is this a mirror matchup: 0 = mirror
            #     int<lower=1, upper=NC> char1V[NVG]; // Character 1 in game
            #     int<lower=1, upper=NC> char2V[NVG]; // Character 2 in game
            #     int<lower=1, upper=NP> player1V[NVG]; // Player 1 in game
            #     int<lower=1, upper=NP> player2V[NVG]; // Player 2 in game
            #     vector[NVG] elo_logitV; // Player 1 ELO-based logit win chance
            # }

            # parameters {
            #     vector[NM] mu; // Matchup value
            #     vector<upper=0>[NP] char_skill[NC]; // Player skill at character
            #     real<lower=0> elo_logit_scale; // elo_logit scale
            # }
            # model {
            #     for (n in 1:NC) {
            #         char_skill[n] ~ std_normal();
            #     }
            char_skill_deficit = pm.HalfNormal(
                "char_skill_deficit",
                sigma=1.0,
                shape=(self.constant_input["NC"], self.constant_input["NP"]),
            )
            char_skill = pm.Deterministic("char_skill", char_skill_deficit * -1)
            #     mu ~ normal(0, 0.5);
            mu = pm.Normal("mu", 0.0, sigma=0.5, shape=(self.constant_input["NM"]))
            #     elo_logit_scale ~ std_normal();
            elo_logit_scale = pm.HalfNormal("elo_logit_scale", sigma=1.0)

            # transformed parameters {
            #     vector[NTG] win_chance_logit;
            #     for (n in 1:NTG) {
            #         win_chance_logit[n] =
            #             char_skill[char1T[n], player1T[n]] -
            #             char_skill[char2T[n], player2T[n]] +
            #             non_mirrorT[n] * mu[mupT[n]] +
            #             elo_logit_scale * elo_logitT[n];
            #     }
            # }
            win_chance_logit = pm.Deterministic(
                "win_chance_logit",
                char_skill[
                    self.validation_input["char1T"] - 1,
                    self.validation_input["player1T"] - 1,
                ]
                - char_skill[
                    self.validation_input["char2T"] - 1,
                    self.validation_input["player2T"] - 1,
                ]
                + self.validation_input["non_mirrorT"]
                * mu[self.validation_input["mupT"] - 1]
                + elo_logit_scale * self.validation_input["elo_logitT"],
            )

            #     winT ~ bernoulli_logit(win_chance_logit);
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=win_chance_logit,
                observed=self.validation_input["winT"],
            )
            # }
            # generated quantities{
            #     vector[NTG] log_lik;
            #     vector[NTG] win_hat;

            #     for (n in 1:NTG) {
            #         log_lik[n] = bernoulli_logit_lpmf(winT[n] | win_chance_logit[n]);
            #         win_hat[n] = bernoulli_logit_rng(win_chance_logit[n]);
            #     }
            # }
        return model

    def predict(self, games):
        mean_skill = self.fit["posterior"].char_skill.mean(["chain", "draw"])
        skill1 = games.aggregate(
            lambda x: float(mean_skill.sel(character=x.character_1, player=x.player_1)),
            axis=1,
        )
        skill2 = games.aggregate(
            lambda x: float(mean_skill.sel(character=x.character_2, player=x.player_2)),
            axis=1,
        )
        non_mirror = (games.character_1 != games.character_2).astype(int)
        matchup_value = self.fit["posterior"].mu.mean(["chain", "draw"])
        matchup = games.aggregate(
            lambda x: float(
                matchup_value.sel(matchup=f"{x.character_1}-{x.character_2}")
            ),
            axis=1,
        )
        elo_logit_scale = float(
            self.fit["posterior"].elo_logit_scale.mean(["chain", "draw"])
        )
        return expit(
            skill1
            - skill2
            + (non_mirror * matchup)
            + (elo_logit_scale * elo_logit(games))
        )
