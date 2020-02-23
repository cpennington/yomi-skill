from decimal import Decimal
import gambit
import pandas as pd
import numpy as np


class Nash:
    def __init__(self, mu_chart, cast=None):
        self._mu_chart = mu_chart.apply(Decimal)
        if cast:
            self.mu_chart = self._mu_chart.loc[(list(cast), list(cast))]
            self.characters = cast
        else:
            self.mu_chart = self._mu_chart
            self.characters = self.mu_chart.index.levels[0].values
        self._std_cp_payoffs = {}
        self._std_cp_games_played = {}
        self._blind_pick_nash = {}

    @classmethod
    def from_render(cls, render):
        matchups = render.matchups
        win_rates = (
            matchups.groupby(["c1", "c2"]).win_rate.median().rename("median_win_rate")
            / 10
        )
        win_rates.loc[[(c, c) for c in win_rates.index.levels[0].values]] = 0.5
        return cls(win_rates)

    def cast_limited_to(self, cast):
        return Nash(self.mu_chart, cast=cast)

    def win_rate(self, best_of=7):
        wins_required = (best_of + 1) // 2
        return (
            self.mu_chart.to_frame()
            .apply(
                lambda r: self.std_cp_payoff(
                    r.name[0], wins_required, r.name[1], wins_required
                ),
                axis=1,
            )
            .rename("bo{}".format(best_of))
        )

    def blind_pick_nash_eq(self, best_of=7):
        if best_of not in self._blind_pick_nash:

            rates = self.win_rate(best_of=best_of).to_frame()

            def const_sum(row):
                (c1, c2) = row.name
                if c1 > c2:
                    return Decimal(1) - rates.loc[c2, c1][0]
                elif c1 == c2:
                    return Decimal(0.5)
                else:
                    return rates.loc[c1, c2][0]

            rates["const_sum"] = rates.apply(const_sum, axis=1)
            # rates = rates.set_index(['c1', 'c2'])
            rates = rates.const_sum.unstack()
            rates = rates.to_numpy()

            rates = np.array([[round(val, 4) for val in row] for row in rates])
            g = gambit.Game.from_arrays(rates, rates.transpose())
            eqs = gambit.nash.lp_solve(g)
            self._blind_pick_nash[best_of] = list(
                zip(self.characters, np.array(eqs[0][g.players[0]]).astype(float))
            )
        return self._blind_pick_nash[best_of]

    def expected_r1_mus(self, best_of=7):
        nash = self.blind_pick_nash_eq(best_of=best_of)
        return [
            ((p1, p2), p1_n * p2_n)
            for (p1, p1_n) in nash
            for (p2, p2_n) in nash
            if p1_n * p2_n > 0
        ]

    def character_counts(self, best_of=7, p1=True):
        return (
            (
                self.matchup_counts(best_of=best_of)
                .reset_index()
                .groupby("c1" if p1 else "c2")[0]
                .sum()
            )
            .sort_values(ascending=False)
            .astype(float)
            .round(2)
        )

    def matchup_counts(self, best_of=7):
        return (
            self.mu_chart.to_frame()
            .apply(
                lambda r: self.expected_match_count(
                    r.name, self.expected_r1_mus(best_of=best_of)
                ),
                axis=1,
            )
            .sort_values()
        )

    def expected_match_count(self, mu, expected_r1):
        return sum(
            self.std_cp_games_played(mu, p1, 4, p2, 4) * Decimal(expected)
            for ((p1, p2), expected) in expected_r1
        )

    def optimal_counterpics(self, best_of=7):
        wins_required = range(1, ((best_of + 1) // 2) + 1)
        return pd.DataFrame(
            {
                "{}-{}".format(p1_req, p2_req): [
                    min(
                        (self.std_cp_payoff(p1, p1_req, p2, p2_req), p2)
                        for p2 in self.characters
                    )[1]
                    for p1 in self.characters
                ]
                for p1_req in range(1, 5)
                for p2_req in range(1, 5)
            },
            index=self.characters,
        )

    def std_cp_payoff(self, p1_playing, p1_req, p2_playing, p2_req):
        key = (p1_playing, p1_req, p2_playing, p2_req)

        if p1_req == 0:
            return Decimal(1)
        if p2_req == 0:
            return Decimal(0)

        if key not in self._std_cp_payoffs:
            p1_win_chance = self.mu_chart.loc[p1_playing, p2_playing]
            p1_win_rec = min(
                self.std_cp_payoff(p1_playing, p1_req - 1, new_cp, p2_req)
                for new_cp in self.characters
            )
            p2_win_rec = max(
                self.std_cp_payoff(new_cp, p1_req, p2_playing, p2_req - 1)
                for new_cp in self.characters
            )
            self._std_cp_payoffs[key] = (
                p1_win_chance * p1_win_rec + (1 - p1_win_chance) * p2_win_rec
            )

        return self._std_cp_payoffs[key]

    def std_cp_games_played(self, mu, p1_playing, p1_req, p2_playing, p2_req):
        key = (mu, p1_playing, p1_req, p2_playing, p2_req)

        if p1_req == 0:
            return Decimal(0)
        if p2_req == 0:
            return Decimal(0)

        if key not in self._std_cp_games_played:
            p1_win_chance = self.mu_chart.loc[p1_playing, p2_playing]
            p2_cp_payoffs = [
                (self.std_cp_payoff(p1_playing, p1_req - 1, new_cp, p2_req), new_cp)
                for new_cp in self.characters
            ]
            p2_best_cp_payoff, p2_cp = min(p2_cp_payoffs)
            p2_played_rec = self.std_cp_games_played(
                mu, p1_playing, p1_req - 1, p2_cp, p2_req
            )
            p1_cp_payoffs = [
                (self.std_cp_payoff(new_cp, p1_req, p2_playing, p2_req - 1), new_cp)
                for new_cp in self.characters
            ]
            p1_best_cp_payoff, p1_cp = max(p1_cp_payoffs)
            p1_played_rec = self.std_cp_games_played(
                mu, p1_cp, p1_req, p2_playing, p2_req - 1
            )
            played_one = 1 if mu == (p1_playing, p2_playing) else 0

            self._std_cp_games_played[key] = (
                played_one
                + p1_win_chance * p2_played_rec
                + (1 - p1_win_chance) * p1_played_rec
            )

        return self._std_cp_games_played[key]
