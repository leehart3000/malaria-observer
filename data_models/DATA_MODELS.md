# Data Models

A `Dataset` is the authoritative domain object representing an externally
provided collection of data. A dataset may exist without any editorial
content. Dataset releases that supersede one another (e.g. Pf7 → Pf8) are currently modelled as independent `Dataset` records with no formal versioning relationship between them. A "dataset family" or version-lineage concept may be introduced later if the site needs to represent that relationship explicitly (e.g. "this is the latest release of X"). `Dataset` is registered as a Wagtail Snippet and is searchable via Wagtail's search framework.


`SampleRecord` belongs to exactly one `Dataset`. Sample identifiers are
unique within a dataset, but are not globally unique. Consequently, the same
sample identifier may occur in multiple datasets. Contributing studies are currently stored only as free text (`study`) on `SampleRecord`; a dedicated many-to-many model may be introduced later if the site needs to describe individual research projects directly.

A `DatasetPage` is optional Wagtail editorial content describing a `Dataset`.
It is not the authoritative representation of the dataset and is not required
for importing or exploring its records.

`DatasetIndexPage` is the Wagtail collection/landing page for datasets.

Scientific studies, projects, publications, and other research context are
editorial/domain concepts that may be introduced separately where there is a
clear requirement. They are not assumed to correspond one-to-one with
datasets.

A `Dataset` may be integrated into the system without being exposed through
the normal Wagtail dataset navigation.

A `DatasetPage` represents the editorial publication of a dataset. The
`DatasetIndexPage` lists published `DatasetPage` objects, not every `Dataset`
record in the system.

Consequently, creating a `Dataset` does not by itself make it appear in the
dataset navigation. A maintainer can create and populate a `Dataset` before
deciding that it is ready for an editorial page.

The data explorers operate directly on `Dataset` records and therefore do
not require a `DatasetPage`.