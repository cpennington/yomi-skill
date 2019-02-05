from IPython.core.display import display
from plotnine import *
from character import *
from cached_property import cached_property

def extract_index(col_name):
    field, _, rest = col_name.partition('[')
    indices = [int(idx) for idx in rest[:-1].split(',')]
    return field, indices

class YomiRender:
    def __init__(self, model, warmup=1000, min_samples=1000):
        self.model = model
        self.warmup = warmup
        self.min_samples = min_samples

    @property
    def results_df(self):
        return self.model.sample_dataframe(warmup=self.warmup, min_samples=self.min_samples)

    @cached_property
    def player_category(self):
        return pandas.api.types.CategoricalDtype(self.model.player_index.keys(), ordered=True)


    @cached_property
    def player_tournament_skill(self):
        results = self.results_df
        reverse_player_tournament_index = {ix: (player, tournament) for ((player, tournament), ix) in self.model.player_tournament_index.items()}

        tournament_category = pandas.api.types.CategoricalDtype(self.model.tournament_index.keys(), ordered=True)

        player_tournament_skill = results[[col for col in results.columns if col.startswith('skill[')]].unstack().rename('skill').reset_index()
        player_tournament_skill['player'] = player_tournament_skill.level_0.apply(
            lambda x: reverse_player_tournament_index[int(x[6:-1])][0]
        ).astype(self.player_category)
        player_tournament_skill['tournament'] = player_tournament_skill.level_0.apply(
            lambda x: reverse_player_tournament_index[int(x[6:-1])][1]
        ).astype(tournament_category)

        del(player_tournament_skill['level_0'])
        player_tournament_skill = player_tournament_skill.rename(columns={'level_1': 'sample'})
        tournament_list = self.model.games.groupby('tournament_name').match_date.quantile(0.5).sort_values().index.tolist()

        player_tournament_skill['tournament'] = player_tournament_skill['tournament'].cat.reorder_categories(tournament_list, ordered=True )
        return player_tournament_skill

    @cached_property
    def raw_player_tournament_skill(self):
        results = self.results_df
        reverse_player_tournament_index = {ix: (player, tournament) for ((player, tournament), ix) in self.model.player_tournament_index.items()}

        tournament_category = pandas.api.types.CategoricalDtype(self.model.tournament_index.keys(), ordered=True)

        player_tournament_skill = results[[col for col in results.columns if col.startswith('raw_skill[')]].unstack().rename('raw_skill').reset_index()
        player_tournament_skill['player'] = player_tournament_skill.level_0.apply(
            lambda x: reverse_player_tournament_index[extract_index(x)[1][0]][0]
        ).astype(self.player_category)
        player_tournament_skill['tournament'] = player_tournament_skill.level_0.apply(
            lambda x: reverse_player_tournament_index[extract_index(x)[1][0]][1]
        ).astype(tournament_category)

        del(player_tournament_skill['level_0'])
        player_tournament_skill = player_tournament_skill.rename(columns={'level_1': 'sample'})
        tournament_list = self.model.games.groupby('tournament_name').match_date.quantile(0.5).sort_values().index.tolist()

        player_tournament_skill['tournament'] = player_tournament_skill['tournament'].cat.reorder_categories(tournament_list, ordered=True )
        return player_tournament_skill

    @cached_property
    def player_char_skill(self):
        results = self.results_df
        reverse_player_index = {ix: player for (player, ix) in self.model.player_index.items()}
        reverse_character_index = {ix: char for (char, ix) in self.model.character_index.items()}

        player_char_skill = results[[col for col in results.columns if col.startswith('char_skill[')]].unstack().rename('char_skill').reset_index()
        player_char_skill['player'] = player_char_skill.level_0.apply(
            lambda x: reverse_player_index[int(x[11:-1].split(',')[1])]
        ).astype(self.player_category)
        player_char_skill['character'] = player_char_skill.level_0.apply(
            lambda x: reverse_character_index[int(x[11:-1].split(',')[0])]
        ).astype(character_category)

        del(player_char_skill['level_0'])
        player_char_skill = player_char_skill.rename(columns={'level_1': 'sample'})
        return player_char_skill

    def render_player_skill(self, player):
        player_skill = self.player_tournament_skill[self.player_tournament_skill.player == player]
        player_chart = (
            ggplot(player_skill, aes(x='tournament', y='skill'))
            + geom_violin()
            + geom_line(player_skill.groupby('tournament').median().reset_index().dropna())
            + theme(
                figure_size=(player_skill.tournament.nunique()*.2, 2),
                axis_text_x=element_text(rotation=90),
            )
            + labs(title=player)
        )
        player_chart.save(f'{player}-skill-{self.model.model_hash}-{self.model.data_hash}.png')

    def render_raw_player_skill(self, player):
        player_skill = self.raw_player_tournament_skill[self.raw_player_tournament_skill.player == player]
        display(self.raw_player_tournament_skill.player.unique())
        player_chart = (
            ggplot(player_skill, aes(x='tournament', y='raw_skill'))
            + geom_violin()
            + geom_line(player_skill.groupby('tournament').median().reset_index().dropna())
            + theme(
                figure_size=(player_skill.tournament.nunique()*.2, 2),
                axis_text_x=element_text(rotation=90),
            )
            + labs(title=player)
        )
        player_chart.save(f'{player}-raw-skill-{self.model.model_hash}-{self.model.data_hash}.png')

    def render_char_skill(self, player):
        char_skill = self.player_char_skill[self.player_char_skill.player == player]
        char_skill_chart = (
            ggplot(char_skill, aes(x='character', y='char_skill'))
            + geom_violin()
            + theme(
                figure_size=(char_skill.character.nunique()*.2, 2),
                axis_text_x=element_text(rotation=90),
            )
            + labs(title=player)
        )
        char_skill_chart.save(f'{player}-char-skill-{self.model.model_hash}-{self.model.data_hash}.png')

    def render_player_skills(self, *players):
        for player in players:
            self.render_player_skill(player)

    def render_raw_player_skills(self, *players):
        for player in players:
            self.render_raw_player_skill(player)
