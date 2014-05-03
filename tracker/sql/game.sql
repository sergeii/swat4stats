CREATE INDEX ON tracker_game (date_finished DESC);
CREATE INDEX ON tracker_game ((score_swat+score_sus) DESC);
CREATE INDEX tracker_game_mapname ON tracker_game (mapname NULLS LAST);
CLUSTER tracker_game USING tracker_game_mapname;