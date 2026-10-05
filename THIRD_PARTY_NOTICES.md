# License scope and third party notices

## Project contributions

The root [MIT license](LICENSE) applies to the project's original software in `code/`, `scripts/`, `tests/`, original archive-processing programs, Makefile, workflow and runtime configuration. It also permits reuse of the software-specific instructions accompanying that software. Component-specific third-party notices below take precedence for those components.

[LICENSE_DATA.md](LICENSE_DATA.md) applies CC BY 4.0 to the project's original data compilation, annotations, analytical documentation, computed results, figures and report text, to the extent the contributors hold those rights. Original government source material and third-party content keep their original rights and terms. No blanket license over all input material is granted.

The maintainer attribution **ByronLi0207** identifies the repository account. It is not a statement of the paper's human author list or affiliations.

## PCG random number component

The PCG32 XSH-RR component follows the PCG implementation by M. E. O'Neill, copyright 2014, licensed under Apache License 2.0. The project implements the generator in JavaScript using BigInt arithmetic and adds state serialization for reproducible numerical calculations.

Component locations:

- `code/reference_core.js` — PCG32 class; the surrounding project-specific statistical routines have their separate project license.
- `inputs/reference_experiments/T1_source/reference_core.js` — archived reference implementation containing the same component.
- `inputs/reference_experiments/T4b_source/screened_reference_core.js` — archived screened-reference implementation containing the component.

The archived input copies are preserved as supplied. The Apache 2.0 license text is distributed in [environment/LICENSE_PCG_APACHE_2.0.txt](environment/LICENSE_PCG_APACHE_2.0.txt). Upstream information: [PCG downloads](https://www.pcg-random.org/download.html) and [pcg-c source](https://github.com/imneme/pcg-c).

## Runtime dependencies

Python, Node.js, NumPy, pandas, SciPy, Matplotlib, python-docx, lxml, PyMuPDF and LibreOffice are third-party dependencies. Their own distributions supply the applicable licenses. This archive supplies dependency specifications rather than redistributing those runtime binaries.

## Government source archive

County quotations and captured responses originate from the Liaoning price-monitoring archive; the national circulation-price series originates from the National Bureau of Statistics. Source URLs, observation states and original records are retained in the inputs. The project does not relicense original government webpages or third-party content. Check the relevant publisher's terms before redistributing them.

## Chinese document font

The Agri Serif SC character subset derived from Noto Serif CJK SC Regular in `assets/fonts/` is distributed under the SIL Open Font License 1.1. Its license is included at `assets/fonts/LICENSE.txt`; source and rendering instructions appear in `assets/fonts/README.md`. This font is separate from the MIT project code and CC BY project documentation.
