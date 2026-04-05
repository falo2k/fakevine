# Changelog

## 0.1.0 (2026-04-05)


### Features

* /health endpoint for docker health checks ([9670e9c](https://github.com/falo2k/fakevine/commit/9670e9c50395e46d0e11383361a8301e45dc3665))
* added all remaining comic routes for db source and enhanced detailvolume model ([eed2b36](https://github.com/falo2k/fakevine/commit/eed2b36552a1a2319304b60ff4cd2382bed5bbf4))
* added log interception and exception handling for validation errors ([e0f00a4](https://github.com/falo2k/fakevine/commit/e0f00a408e7d9c2df352b04a645be6059a2e4bb6))
* added param validation framework to cvrouter for requests ([f58c7bd](https://github.com/falo2k/fakevine/commit/f58c7bdfc3d51e9f043cba4316be06f395d76fbb))
* added user agent setting for CV cache ([77cb0fb](https://github.com/falo2k/fakevine/commit/77cb0fbd71832725fce26124eb82a3ddd780beda))
* basic cv reddit db converter + model fixes ([ab6e381](https://github.com/falo2k/fakevine/commit/ab6e381ab02f12047d79f61b3c29db47534d3328))
* basic jsonp support ([32b1c8f](https://github.com/falo2k/fakevine/commit/32b1c8fbb8135ada806360c2ccb89000ee4e136f))
* **cache-trunk:** made single cachedsession and implemented bypasses ([b46b706](https://github.com/falo2k/fakevine/commit/b46b7063510b85f6669608241acfc8380e7fe83c))
* changed configuration to use dynaconf (toml + env) ([6fe61f7](https://github.com/falo2k/fakevine/commit/6fe61f7f7ff54db24b4c75230e5cbf8a4ff00b85))
* changed static db to wal for future updates ([9cdca91](https://github.com/falo2k/fakevine/commit/9cdca91c1949700081b36357467ce7771a97e578))
* **cvapimodels:** additional models and some refactoring to use generics ([4ddcad5](https://github.com/falo2k/fakevine/commit/4ddcad596efe91b84174efd12c376c33c0a17107))
* **cvapimodels:** cleaned up some models to reflect state of CV data and added character response model ([48150a1](https://github.com/falo2k/fakevine/commit/48150a19f528aa5c2f3c4bfd9a7e7d34f60c5962))
* **cvapimodels:** implemented remaining comic models, pre-consolidation ([4585a26](https://github.com/falo2k/fakevine/commit/4585a26cea2f84f6290df8bfb85ad3abf7ec27b2))
* dockerfile and dev dockerfile with debugpy + launch config ([d6fe125](https://github.com/falo2k/fakevine/commit/d6fe12577ec31d572edeb7970c17a5c6a29b67e0))
* extended dbmodels for relationships ([c2c6e2d](https://github.com/falo2k/fakevine/commit/c2c6e2d11fb33e7b50031c594629ac0d682aeb9a))
* extended params validation to all comic routes and better date validation ([856e0b5](https://github.com/falo2k/fakevine/commit/856e0b552057510ab2c4ec474e3520f54e9c67e6))
* fts search endpoint support for static db trunk ([c64896d](https://github.com/falo2k/fakevine/commit/c64896db4630d89123edf394046cfd42a08cb576))
* fts tables, triggers, and index build on convert added to staticdb + indexes on reference keys ([333eae1](https://github.com/falo2k/fakevine/commit/333eae196f963104475bfd70159c446227049e15))
* implemeneted a less than ideal solution for field_list and extended validation to single response routes ([87d48ee](https://github.com/falo2k/fakevine/commit/87d48eebcff237842743b5955e81367bef4d2f48))
* implemented reference for filter and sort for list endpoints in /characters on db trunk ([07ddfc7](https://github.com/falo2k/fakevine/commit/07ddfc7eae8cab3674f1263de9b737f7b6ff2e5f))
* implemented remaining routes, added retries to cache, gateway error handling ([e9656fc](https://github.com/falo2k/fakevine/commit/e9656fcf63206bba8d14d3fa84781dccf299f48c))
* initial framework for utils (scripts) and a simple DB ([30971af](https://github.com/falo2k/fakevine/commit/30971af66fbf816816372523e6511609eb2c4e3e))
* Initial structure, example cache implementation ([5418a60](https://github.com/falo2k/fakevine/commit/5418a60a272950e3aae3a4097ef210cdf7d056f6))
* localcvdb support ([7c28bf7](https://github.com/falo2k/fakevine/commit/7c28bf734edaf094820312f7a99ab59ffa4b01c0))
* models for concept and issue ([42127c5](https://github.com/falo2k/fakevine/commit/42127c59065ccc66282dd0f9d8cd136f27e4ca8b))
* refactored db methods and implemented concept/concepts sources ([4ff3d16](https://github.com/falo2k/fakevine/commit/4ff3d16a793bdba5f53fa667b113b37645fd2b8b))
* refactoring to change the way field_list is applied, allowing trunks to handle for speed ([396f657](https://github.com/falo2k/fakevine/commit/396f657217693574fbe1d5fa5025e8c1f43e73e8))
* sample docker setup for rate limiting and caching using caddy ([918e315](https://github.com/falo2k/fakevine/commit/918e315c264fdaa7241035855356ca0edfd87b6f))
* shoving asyncio into sql backend ([0c5c428](https://github.com/falo2k/fakevine/commit/0c5c4288e947a3e5f601a069b3ddadaf325fb6b9))
* **simple_cache_trunk:** asyncio support on cache trunk ([f69ad95](https://github.com/falo2k/fakevine/commit/f69ad9564e078cad11f5705eeda5455cc72e3267))
* support a list of api keys in config, and better checks on missing keys ([42bad95](https://github.com/falo2k/fakevine/commit/42bad95899901805419f6666f4e785b8e5f1accf))
* support validation of filter/sort params on search route ([73834c4](https://github.com/falo2k/fakevine/commit/73834c40860f712434faf4da9ca41eb446c91e22))
* updated cv routes to handle url format errors, added stub for static db trunk, changed cache timing to minutes ([a4e8b89](https://github.com/falo2k/fakevine/commit/a4e8b89fac6df150b683c4ab56d821355c9ab6c6))
* xml response support ([cc524e2](https://github.com/falo2k/fakevine/commit/cc524e2f561f5d9765fb5ab499ab0d83388a880b))


### Bug Fixes

* add curl to docker image for health check ([af36d3d](https://github.com/falo2k/fakevine/commit/af36d3d99de84e6546690085e6411a3c17a4f04c))
* allow cleanup to fail gracefully in absence of packages ([18a7c68](https://github.com/falo2k/fakevine/commit/18a7c684a735b7b8ec40a76986d94a8f1c8c1795))
* bumped sqlaclhemy to 2.1pre, fixed some JSON parsing, refactored dupe handling ([3a8a528](https://github.com/falo2k/fakevine/commit/3a8a52820f241744796bcded9fdf5140b012e667))
* **cvapimodels:** fixed type checking error on equality function + documented assumptions ([12812b7](https://github.com/falo2k/fakevine/commit/12812b7b1bdf376de6fc0f2d559e48f22db30d61))
* **cvrouter:** removed bogus route ([d47c261](https://github.com/falo2k/fakevine/commit/d47c2617da6165000f87093cef54d98920654759))
* fix to person endpoint, change not implemented message to a warning, updated README ([e61310e](https://github.com/falo2k/fakevine/commit/e61310eb7618fe3d32c79c9f27672844c801c2ac))
* fixed missing lxml import in pyproject ([5fb72cd](https://github.com/falo2k/fakevine/commit/5fb72cd9b5aae058fe99c26b285cb9a466c04053))
* handled bad cv routes ([df55302](https://github.com/falo2k/fakevine/commit/df55302ebb2867e697444b881853e4b8a7ca626c))
* i may have missed volume id on issues ([11549d7](https://github.com/falo2k/fakevine/commit/11549d7c21c23187aaecc56ca50fd24c2eb1f97f))
* log file name configurable to allow writing to docker persistent storage ([4ad80b4](https://github.com/falo2k/fakevine/commit/4ad80b419c65581314ba6551e7e391165b9389ba))
* **model.helpers:** ensure empty person.death data is stored as sql null, not json null ([92ccf3e](https://github.com/falo2k/fakevine/commit/92ccf3e91334249d3f35a2ac943b928c13bb8051))
* **pyproject.toml:** missing types-lxml for type checking ([67c9bf8](https://github.com/falo2k/fakevine/commit/67c9bf841541d9f080fd528c033a4d8bf8268903))
* **tests:** fixed cvapimodel tests to match changes to case sensitivity ([17cd4f4](https://github.com/falo2k/fakevine/commit/17cd4f4978fd275b8ac22cce96a488b13730defa))
* **tests:** fixing tests after last changes ([25eafae](https://github.com/falo2k/fakevine/commit/25eafaed423615b40a7f67f385aceccbab81c4a4))
* tweak to string cleanup for fts query ([6c39fd2](https://github.com/falo2k/fakevine/commit/6c39fd22bce56afb79730bc679361fa96abc9697))
* type hint dodginess in static db ([052bc70](https://github.com/falo2k/fakevine/commit/052bc70f4df0fe7a69f1b29a2a487377f1c844a8))
* typo on healthcheck endpoint name for fakevine ([a5e1b98](https://github.com/falo2k/fakevine/commit/a5e1b9832dfac2c8d4575a8be4851d41174ac5aa))
* wrong total results count on list sources ([8573069](https://github.com/falo2k/fakevine/commit/85730692ac0e35509516183f9a412d2a7042fe44))
* **xml-responses:** fixed missing mappings ([3dfaf69](https://github.com/falo2k/fakevine/commit/3dfaf69394ee9f27645778b905b62e6894fa37ec))


### Documentation

* documentation for backend trunks ([a026183](https://github.com/falo2k/fakevine/commit/a026183ee261ae6a16eea62ace002e3e37834704))
* readme tweaks ([9089aee](https://github.com/falo2k/fakevine/commit/9089aee069e519b7d162e344650827718883e5bb))
