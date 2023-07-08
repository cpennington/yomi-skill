import React, { Component } from "react";
import logo from "./logo.svg";
import "./App.css";

class App extends Component {
  render() {
    return (
      <Router>
        <div className="App">
          <nav class="nav nav-tabs">
            <a
              class="nav-link ${'active' if self.attr.game == 'yomi' else ''}"
              href="/yomi-skill"
            >
              Yomi Skill Chart
            </a>
          </nav>
          <div class="container">
            <div class="div-group row col-12 mt-2">
              <label for="player" class="col-sm-auto col-form-label">
                Player:
              </label>
              <input
                list="players"
                id="player"
                name="player"
                class="col-sm-3 form-control"
              />
              <label for="opponent" class="col-sm-auto col-form-label">
                Opponent:
              </label>
              <input
                list="players"
                id="opponent"
                name="opponent"
                class="col-sm-3 form-control"
              />
              <div class="col-sm-3 justify-content-between">
                <button
                  id="graph"
                  onclick="return doGraph();"
                  class="col-sm-9 btn btn-primary justify-content-end"
                >
                  Graph
                </button>
                <div id="loading" class="col-sm-1 justify-content-end">
                  <img id="arrows" src="${static_root}/loading.svg" />
                </div>
              </div>
              <datalist id="players" />
            </div>
            <div id="against-cfg" class="div-group row col-12 mt-2">
              <label
                for="against-elo"
                class="col-sm-auto col-form-label col-form-label-sm"
              >
                Against Elo:
              </label>

              <div
                id="against-elo"
                class="btn-group btn-group-toggle"
                data-toggle="buttons"
              >
                <label class="btn btn-secondary btn-sm active">
                  <input
                    type="radio"
                    name="against-elo"
                    id="against-elo-self"
                    autocomplete="off"
                    value="self"
                    checked
                  />
                  Own
                </label>
                <label class="btn btn-secondary btn-sm">
                  <input
                    type="radio"
                    name="against-elo"
                    id="against-elo-5"
                    autocomplete="off"
                    value="5%"
                  />
                  5%
                </label>
                <label class="btn btn-secondary btn-sm">
                  <input
                    type="radio"
                    name="against-elo"
                    id="against-elo-25"
                    autocomplete="off"
                    value="25%"
                  />
                  25%
                </label>
                <label class="btn btn-secondary btn-sm">
                  <input
                    type="radio"
                    name="against-elo"
                    id="against-elo-50"
                    autocomplete="off"
                    value="50%"
                  />
                  50%
                </label>
                <label class="btn btn-secondary btn-sm">
                  <input
                    type="radio"
                    name="against-elo"
                    id="against-elo-75"
                    autocomplete="off"
                    value="75%"
                  />
                  75%
                </label>
                <label class="btn btn-secondary btn-sm">
                  <input
                    type="radio"
                    name="against-elo"
                    id="against-elo-95"
                    autocomplete="off"
                    value="95%"
                  />
                  95%
                </label>
                <label class="btn btn-secondary btn-sm">
                  <input
                    type="radio"
                    name="against-elo"
                    id="against-elo-max"
                    autocomplete="off"
                    value="100%"
                  />
                  Max
                </label>
              </div>
              <label
                for="against-skill"
                class="col-sm-auto col-form-label col-form-label-sm"
              >
                Against Char Skill:
              </label>

              <div
                id="against-skill"
                class="btn-group btn-group-toggle"
                data-toggle="buttons"
              >
                <label class="btn btn-secondary btn-sm active">
                  <input
                    type="radio"
                    name="against-skill"
                    autocomplete="off"
                    value="self"
                    checked
                  />
                  Own
                </label>
                <label class="btn btn-secondary btn-sm">
                  <input
                    type="radio"
                    name="against-skill"
                    autocomplete="off"
                    value="5%"
                  />
                  5%
                </label>
                <label class="btn btn-secondary btn-sm">
                  <input
                    type="radio"
                    name="against-skill"
                    autocomplete="off"
                    value="25%"
                  />
                  25%
                </label>
                <label class="btn btn-secondary btn-sm">
                  <input
                    type="radio"
                    name="against-skill"
                    autocomplete="off"
                    value="50%"
                  />
                  50%
                </label>
                <label class="btn btn-secondary btn-sm">
                  <input
                    type="radio"
                    name="against-skill"
                    autocomplete="off"
                    value="75%"
                  />
                  75%
                </label>
                <label class="btn btn-secondary btn-sm">
                  <input
                    type="radio"
                    name="against-skill"
                    autocomplete="off"
                    value="95%"
                  />
                  95%
                </label>
                <label class="btn btn-secondary btn-sm">
                  <input
                    type="radio"
                    name="against-skill"
                    autocomplete="off"
                    value="100%"
                  />
                  Max
                </label>
              </div>
            </div>
            <table id="player-stats" class="table table-hover table-sm mt-2">
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Elo</th>
                  <th>Games recorded</th>
                </tr>
              </thead>
              <tbody>
                <tr id="p1-stats">
                  <td id="p1-name" />
                  <td id="p1-elo" />
                  <td id="p1-games" />
                </tr>
                <tr id="p2-stats">
                  <td id="p2-name" />
                  <td id="p2-elo" />
                  <td id="p2-games" />
                </tr>
              </tbody>
            </table>
            <div class="row col-12">
              <div id="contribute" />
            </div>
          </div>
          <div id="vis" />
          <div id="player-vis" />
        </div>
      </Router>
    );
  }
}

export default App;
