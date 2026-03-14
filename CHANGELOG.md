# Changelog

## 0.1.0 (2026-03-14)


### Features

* added log interception and exception handling for validation errors ([e0f00a4](https://github.com/falo2k/fakevine/commit/e0f00a408e7d9c2df352b04a645be6059a2e4bb6))
* added param validation framework to cvrouter for requests ([f58c7bd](https://github.com/falo2k/fakevine/commit/f58c7bdfc3d51e9f043cba4316be06f395d76fbb))
* basic cv reddit db converter + model fixes ([ab6e381](https://github.com/falo2k/fakevine/commit/ab6e381ab02f12047d79f61b3c29db47534d3328))
* **cvapimodels:** additional models and some refactoring to use generics ([4ddcad5](https://github.com/falo2k/fakevine/commit/4ddcad596efe91b84174efd12c376c33c0a17107))
* **cvapimodels:** cleaned up some models to reflect state of CV data and added character response model ([48150a1](https://github.com/falo2k/fakevine/commit/48150a19f528aa5c2f3c4bfd9a7e7d34f60c5962))
* **cvapimodels:** implemented remaining comic models, pre-consolidation ([4585a26](https://github.com/falo2k/fakevine/commit/4585a26cea2f84f6290df8bfb85ad3abf7ec27b2))
* extended params validation to all comic routes and better date validation ([856e0b5](https://github.com/falo2k/fakevine/commit/856e0b552057510ab2c4ec474e3520f54e9c67e6))
* implemeneted a less than ideal solution for field_list and extended validation to single response routes ([87d48ee](https://github.com/falo2k/fakevine/commit/87d48eebcff237842743b5955e81367bef4d2f48))
* implemented remaining routes, added retries to cache, gateway error handling ([e9656fc](https://github.com/falo2k/fakevine/commit/e9656fcf63206bba8d14d3fa84781dccf299f48c))
* initial framework for utils (scripts) and a simple DB ([30971af](https://github.com/falo2k/fakevine/commit/30971af66fbf816816372523e6511609eb2c4e3e))
* Initial structure, example cache implementation ([5418a60](https://github.com/falo2k/fakevine/commit/5418a60a272950e3aae3a4097ef210cdf7d056f6))
* models for concept and issue ([42127c5](https://github.com/falo2k/fakevine/commit/42127c59065ccc66282dd0f9d8cd136f27e4ca8b))
* support validation of filter/sort params on search route ([73834c4](https://github.com/falo2k/fakevine/commit/73834c40860f712434faf4da9ca41eb446c91e22))
* updated cv routes to handle url format errors, added stub for static db trunk, changed cache timing to minutes ([a4e8b89](https://github.com/falo2k/fakevine/commit/a4e8b89fac6df150b683c4ab56d821355c9ab6c6))


### Bug Fixes

* bumped sqlaclhemy to 2.1pre, fixed some JSON parsing, refactored dupe handling ([3a8a528](https://github.com/falo2k/fakevine/commit/3a8a52820f241744796bcded9fdf5140b012e667))
* **cvapimodels:** fixed type checking error on equality function + documented assumptions ([12812b7](https://github.com/falo2k/fakevine/commit/12812b7b1bdf376de6fc0f2d559e48f22db30d61))
* **cvrouter:** removed bogus route ([d47c261](https://github.com/falo2k/fakevine/commit/d47c2617da6165000f87093cef54d98920654759))
* handled bad cv routes ([df55302](https://github.com/falo2k/fakevine/commit/df55302ebb2867e697444b881853e4b8a7ca626c))
* **model.helpers:** ensure empty person.death data is stored as sql null, not json null ([92ccf3e](https://github.com/falo2k/fakevine/commit/92ccf3e91334249d3f35a2ac943b928c13bb8051))
* **tests:** fixed cvapimodel tests to match changes to case sensitivity ([17cd4f4](https://github.com/falo2k/fakevine/commit/17cd4f4978fd275b8ac22cce96a488b13730defa))
