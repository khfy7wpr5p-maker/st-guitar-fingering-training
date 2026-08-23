# Third-party notices

Direct Python dependencies and build tooling currently declared by the
project are:

- `defusedxml` >=0.7,<1 — PSF-2.0-style terms.
- `numpy` >=1.26 — BSD-3-Clause.
- `scikit-learn` >=1.4 — BSD-3-Clause; runtime transitives include SciPy,
  joblib, and threadpoolctl under permissive BSD-family terms.
- `setuptools` >=70 — MIT (build tooling).

The exact transitive versions are not locked. Before distributing a wheel,
container, desktop bundle, or other binary, freeze the resolved dependency
graph and ship the exact required license/notice bundle.

The data-extraction workflow uses `PyGuitarPro` 0.10.2 under LGPL-3.0-only.
It is a tooling dependency and is not bundled in the project artifact. If it
is redistributed, all applicable LGPL source, relinking/modification, and
notice obligations must be satisfied.

Dataset and fixture notices are recorded in `DATASET-LICENSES.md`. This
summary does not replace upstream license texts.

