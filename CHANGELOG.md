# Version history

We follow [Semantic Versions](https://semver.org/) since the `0.1.0` release.

Semantic versioning in our case means:
- Bugfixes do not bring new features, code that passes on `x.y.0` should pass on `x.y.1`. With the only exception that bugfix can raise old violations in new places, if they were hidden by a buggy behaviour.
- Minor releases do bring new features and configuration options. New violations can be added. Code that passes `x.0.y` might not pass on `x.1.y` release.
- Major releases inidicate significant milestones or serious breaking changes.

 
## 1.0.0

### Initial

- Initial version. All modules are stable and applicable in production.