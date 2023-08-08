
type EloSkill = { elo: number; gamesPlayed: number };
type GlickoSkill = {
    glickoR: number;
    glickoRD: number;
    glickoV: number;
    gamesPlayed: number;
};
type PlayerSkill = EloPlayerSkill | GlickoPlayerSkill;
type EloPlayerSkill = { char: Record<string, EloSkill> } & EloSkill;
type GlickoPlayerSkill = {
    char: Record<string, GlickoSkill>;
} & GlickoSkill;
type Quantiles = { qs: number[]; std: number };
type EloQuantiles = { elo: Quantiles };
type GlickoQuantiles = { glicko: { r: Quantiles, rd: Quantiles, v: Quantiles } };
type RatingQuantiles = EloQuantiles & GlickoQuantiles;
type AggregatePlayerSkill = {
    globalSkill: RatingQuantiles,
    characters: Record<string, RatingQuantiles & { glicko: { top20: { player: string, r: number, rd: number, v: number }[] } }>
};
type Scales = EloScales | GlickoScales;
type EloScales = {
    eloScaleMean: number;
    eloScaleStd: number;
    eloFactor: number;
    pcEloScaleMean: number;
    pcEloScaleStd: number;
    pcEloFactor: number;
};
type GlickoScales = {
    glickoScaleMean?: number;
    glickoScaleStd?: number;
    glickoFactor?: number;
    pcGlickoScaleMean?: number;
    pcGlickoScaleStd?: number;
    pcGlickoFactor?: number;
    playerGlobalScaleMean?: number;
    playerGlobalScaleStd?: number;
};
type MUStats = {
    count: number;
    mean: number;
    std: number;
};
type MatchupData = Record<string, Record<string, MUStats>>;
type Match = {
    "elo__ro": number;
    "elo__rp": number;
    "glicko__prob": number,
    "glicko__rdo": number,
    "glicko__rdp": number,
    "glicko__ro": number,
    "glicko__rp": number,
    "glicko__vo": number,
    "glicko__vp": number,
    "matchup__character_o": string,
    "matchup__character_p": string,
    "matchup__mup": string,
    "matchup__non_mirror": number,
    "min_games__min_games_player_o": boolean,
    "min_games__min_games_player_p": boolean,
    "min_games__player_o": string,
    "min_games__player_p": string,
    "opponent": string,
    "pc_glicko__prob": number,
    "pc_glicko__rdo": number,
    "pc_glicko__rdp": number,
    "pc_glicko__ro": number,
    "pc_glicko__rp": number,
    "pc_glicko__vo": number,
    "pc_glicko__vp": number,
    "player": string,
    "render__match_date": number,
    "render__public": boolean,
    "render__win": number
}