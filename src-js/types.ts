
export type EloSkill = { elo: number; gamesPlayed: number };
export type GlickoSkill = {
    glickoR: number;
    glickoRD: number;
    glickoV: number;
    gamesPlayed: number;
};
export type PlayerSkill = EloPlayerSkill | GlickoPlayerSkill;
export type EloPlayerSkill = { char: Record<string, EloSkill> } & EloSkill;
export type GlickoPlayerSkill = {
    char: Record<string, GlickoSkill>;
} & GlickoSkill;
export type Quantiles = { qs: number[]; std: number };
export type EloQuantiles = { elo: Quantiles };
export type GlickoQuantiles = { glicko: { r: Quantiles, rd: Quantiles, v: Quantiles } };
export type RatingQuantiles = EloQuantiles & GlickoQuantiles;
export type AggregatePlayerSkill = {
    globalSkill: RatingQuantiles,
    characters: Record<string, RatingQuantiles & { glicko: { top20: { player: string, r: number, rd: number, v: number }[] } }>
};
export type Scales = EloScales | GlickoScales;
export type EloScales = {
    eloScaleMean: number;
    eloScaleStd: number;
    eloFactor: number;
    pcEloScaleMean: number;
    pcEloScaleStd: number;
    pcEloFactor: number;
};
export type GlickoScales = {
    glickoScaleMean?: number;
    glickoScaleStd?: number;
    glickoFactor?: number;
    pcGlickoScaleMean?: number;
    pcGlickoScaleStd?: number;
    pcGlickoFactor?: number;
    playerGlobalScaleMean?: number;
    playerGlobalScaleStd?: number;
};
export type MUStats = {
    count: number;
    mean: number;
    std: number;
};
export type MatchupData = Record<string, Record<string, MUStats>>;
export type Match = {
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
};
export type GemEffects = {
    with_gem: Record<string, Record<string, MUStats>>,
    against_gem: Record<string, Record<string, MUStats>>,
};
export type CharacterPlayCounts = { character: string, gamesRecorded: number }[];