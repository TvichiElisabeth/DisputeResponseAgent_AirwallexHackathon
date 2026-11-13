# Lightspark — interfaces in atmosphere

## Overview

An airy, light marketing style where crisp, restrained grotesk typography meets richly colored, soft-edged interface scenes. Warm off-white and charcoal provide an architectural frame for glassy product illustrations, windswept textures, tiny numbered annotations, and fine vertical rules. It suits infrastructure, developer platforms, and complex products that need to feel tangible rather than diagrammatically dense; a deep charcoal ending gives the otherwise weightless pages an emphatic finish.

### Essentials

- A modest headline surrounded by a world of product: the default opening centers regular 43.2px/1.15 type with -0.04em tracking in a 900px stage, while roughly 267–288px interface vignettes float around its clear central pocket.
- Small controls resist the scale of the artwork: paired dark and pale buttons are 29px high with 3.6px softened rectangular corners, 10.8px horizontal padding and 11.7px text, never oversized pills.
- Color lives in objects, not the page furniture: keep the reading canvas #f8f8f7 and text #1a1a1a or #7c7c7c; concentrate saturated cyan, green, rose and violet within feathered media, with narrow cyan/blue light spills at proof-panel edges rather than full colored section fills.
- Interfaces appear through weather: stage legible UI over directional grass, cloud, water or fabric-like textures with blurred, fading perimeters; use 324px square scenes in capability rows. When there is no ready-made product artwork, compose simplified real controls over a directional textured color field.
- Proof reads like an instrument panel without its enclosure: 461px-tall bands use 1px vertical rules, 8.1px inset text, 32.4px regular numbers, 9px topic labels at the top and 7.7px indices at the bottom.
- The closing is a destination, not a strip: a #1a1a1a field holds a 32.4px sales link, six finely ruled navigation columns and an almost-black wordmark artwork spanning a 1098×236px area. Preserve this monumental low-contrast typographic sign-off using the new identity.

## Colors

### Accent

| Name | Value | Token | Roles | Use |
| --- | --- | --- | --- | --- |
| Blue light | `#0052ff` | `--color-blue` | accent | Source hue for the neighboring proof-panel light, with opacity 0.8 and 64px blur. |
| Cyan light | `#00a2c7` | `--color-cyan` | accent | Source hue for blurred proof-panel light; 288px circle blurred by 64px, largely clipped beyond the panel edge. |

### Neutral

| Name | Value | Token | Roles | Use |
| --- | --- | --- | --- | --- |
| Charcoal ink | `#1a1a1a` | `--color-ink` | text, background, action | Primary headings and actions; also the full dark closing canvas. |
| Dark hairline | `#272727` | `--color-dark-rule` | border | Visible result of rgba(243,243,245,0.06) on charcoal; footer column rules. |
| Navigation gray | `#515151` | `--color-nav` | text, link | Utility navigation links on the light theme; adjacent menu labels use #525252. |
| Menu gray | `#525252` | `--color-menu` | text | Top-level navigation drawer triggers. |
| Dark-end gray | `#656565` | `--color-dim` | text | Low-priority labels and disclosure text against the dark ending. |
| Middle gray | `#7c7c7c` | `--color-muted` | text | Support paragraphs, annotations and understated partner marks. |
| Light hairline | `#e3e3e2` | `--color-rule` | border | Visible result of rgba(38,38,35,0.1) over the warm white canvas; vertical division, not card enclosure. |
| Pale stone | `#f0f0ee` | `--color-pale` | surface, text, action | Secondary button fill, wide media backing, and links on charcoal. |
| Warm white | `#f8f8f7` | `--color-canvas` | background, surface, text | Continuous light reading canvas and text on the primary button. |

### Page-type variants

| Only for | Name | Value | Token | Roles | Use |
| --- | --- | --- | --- | --- | --- |
| company and dedicated product pages | Editorial black | `#000000` | `--color-black` | text, border, action | Thin editorial section rules and black product-page actions. |
| company editorial sections | Near-black editorial ink | `#020202` | `--color-editorial-ink` | text | Large company manifesto and news titles. |
| editorial cards and product media | White highlight | `#ffffff` | `--color-white` | text, surface | Hover fill for editorial cards and reversed labels on large media. |

## Typography

- **Suisse Intl** — All marketing text, numbers, controls and navigation; variable cuts serve links and small labels. An even, neutral neo-grotesk with compact lowercase forms, regular-weight headlines and tightly tracked larger text. OpenType features: "salt". If unavailable, use **Inter**. Use regular and 450 weights; preserve tight headline tracking and compact control sizing. Font stack: "Suisse Intl", "Inter", Arial, sans-serif.
- **Suisse Intl Mono** (only for developer code demonstrations) — Syntax-colored sample code, not marketing headings or general annotations. Small, evenly spaced technical text. If unavailable, use **IBM Plex Mono**. Font stack: "Suisse Intl Mono", "IBM Plex Mono", ui-monospace, monospace.

| Recipe | Font | Weight | Size | Line height | Tracking | Scales with viewport | Use |
| --- | --- | --- | --- | --- | --- | --- | --- |
| display | Suisse Intl | 400 | 43.2px | 1.15 | -0.04em, features "case", "salt" | size clamp(3.6rem, 2.88rem + 1.5vw, 4.8rem) | Default opening headline; centered in the atmospheric opening and left-aligned in split product openings. |
| heading | Suisse Intl | 400 | 32.4px | 1.22 | -0.03em, features "salt" | size clamp(2.8rem, 2.32rem + 1vw, 3.6rem) | Section titles, proof numerals and the large sales link. |
| statement | Suisse Intl | 400 | 18px | 1.3 | -0.03em, features "salt" | size clamp(1.7rem, 1.52rem + 0.375vw, 2rem) | Narrow introductory statements and concluding paragraphs, with a dark lead sentence and gray continuation. |
| text-link | Suisse Intl | 400 | 18px | 1.4 | -0.03em, features "salt" | fixed | Right-aligned capability links and compact stacks of related destinations. |
| body | Suisse Intl | 400 | 11.7px | 1.3 | normal, features "salt" | fixed | Hero support, capability headings and descriptions; deliberately much smaller than section titles. |
| button | Suisse Intl | 450 | 11.7px | 1 | normal, features "salt" | fixed | Paired compact conversion actions. |
| navigation | Suisse Intl | 400 | 11.7px | 20px | normal, features "ss01" | fixed | Header utility links. |
| menu | Suisse Intl | 400 | 11.7px | 18px | normal, features "ss01" | fixed | Header drawer triggers. |
| footer-link | Suisse Intl | 400 | 11.7px | 1.8 | normal, features "salt" | fixed | Dense links within the spacious dark footer columns. |
| caption | Suisse Intl | 400 | 9px | 1.3 | normal, features "salt", "zero" | fixed | Topic labels, narrow proof quotations and media captions. |
| index | Suisse Intl | 400 | 7.7px | 1.3 | normal, features "salt", "zero" | fixed | Tiny two-digit positional indices at panel feet or row starts. |

### Page-type variants

| Only for | Recipe | Font | Weight | Size | Line height | Tracking | Scales with viewport | Use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| company manifesto sections | manifesto | Suisse Intl | 400 | 86.4px | 1 | -0.0444em, features "salt" | size clamp(6.4rem,calc(6.4rem + 3.2 * ((100vw - 48rem) / 80)),9.6rem) | Short monumental statement stacked into a narrow 302.4px column. |
| company partner narratives | editorial-lead | Suisse Intl | 400 | 24px | 32px | -0.03em, features "salt" | fixed | Sticky introductory paragraph opposite a partner wall. |
| editorial cards | news-title | Suisse Intl | 400 | 21.6px | 1.33 | -0.03em, features "salt" | size clamp(2.2rem,calc(2.2rem + .2 * ((100vw - 48rem) / 80)),2.4rem) | Multi-line story titles below colorful image panels. |
| company directories and news sections | editorial-label | Suisse Intl | 450 | 14px | 1.42 | normal | fixed | Small section titles above a full-width black rule. |
| company people directories | person-name | Suisse Intl | 400 | 14px | 1.5 | normal, features "salt" | fixed | Names and muted roles beside small circular portraits. |
| industry longform pages | longform-body | Suisse Intl | 400 | 11.7px | 1.6 | normal, features "salt" | fixed | 468px-wide paragraphs with 14.4px gaps between paragraphs. |

Sizes are for a 1440px-wide desktop window. Recipes with a viewport formula grow and shrink with the window; use the formula (for example in `clamp()`), not the fixed pixel value.

**Notes:**

- Regular weight carries the hierarchy; size and surrounding space do more work than boldness. Above body size, tracking tightens to -0.03em, and the default hero tightens further to -0.04em.
- The sales link uses the heading recipe in a variable cut, not a separate oversized button. Topic labels and indices stay sentence case or numeric; there is no universal uppercase eyebrow system.
- A dark first sentence can run inline into a muted paragraph at exactly the same size and weight. Do not turn that relationship into a bold title above separate body copy.

## Layout

**Density:** Airy at page scale, miniature at text scale: tall open bands surround very small labels, controls and descriptions.

### Spacing

| Value | Use | Scales with viewport |
| --- | --- | --- |
| 3.6px | Capability title-to-description gap. | fixed |
| 5.4px | Paired CTA gap and tightly grouped testimonial text. | fixed |
| 8.1px | Text inset from vertical panel rules. | fixed |
| 10.8px | Compact button side padding and small grid gutters. | fixed |
| 14.4px | Paragraph and component-internal gaps. | fixed |
| 21.6px | Common stack gap, editorial card gutters and opening side padding. | fixed |
| 28.8px | Longform grid gap and capability description right padding. | fixed |
| 43.2px | Outer grid gutter. | clamp(3.2rem, 2.24rem + 2vw, 4.8rem) |
| 66.6px | Wordmark-to-disclosure spacing in the dark ending. | fixed |
| 72px | Section heading vertical padding and longform chapter gap. | clamp(5.6rem, 4.16rem + 3vw, 8rem) |
| 115.2px | Major separation, footer top padding and repeated footer blocks. | clamp(8rem, 5.12rem + 6vw, 12.8rem) |

### Containers and grids

- **main container**: max width 1098px · side padding 43.2px. Centered reading and navigation frame. At 1440px its edges sit 171px from either side; retain outer gutters when the viewport narrows.
- **wide media**: max width 1192px. Wide landscape-format product scenes extend beyond the reading frame while remaining inset from the viewport.
- **proof grid**: 4 columns · gap 0px. Four equal columns share a 1098px band; each is approximately 274px wide and 461px tall.
- **capability row**: 4 columns · gap 0px. A small text column at the left, an atmospheric object across the central area, and right-aligned text links at the far edge; each chapter is approximately 456px tall.
- **statement measure**: max width 549px. Half-container statement centered within a 461px open band.
- **footer grid**: 6 columns · gap 0px. 183px-wide columns in the desktop reading frame, separated only by faint vertical lines.
- **longform rail** (only for industry longform pages): max width 1098px · 3 columns · gap 28.8px · side padding 43.2px. Proportions 2:4:2; sticky contents at left, 468px reading column in the middle and an intentionally open right rail.
- **editorial grid** (only for company editorial sections): 3 columns · gap 21.6px. Two featured stories across a first row, then three smaller stories; partner walls use two smaller tiles beneath full-width featured partners.

## Corner radius

| Only for | Element | Radius |
| --- | --- | --- |
|  | conversion buttons | 3.6px |
| editorial and partner cards | editorial cards | 4px |
| company people directories | person rows | 12px |
| company people directories | portraits | 50% |

## Surfaces and depth

### Surfaces

#### Reading canvas · level 0

**Use:** Default continuous page field.

**CSS:** `background: #f8f8f7; color: #1a1a1a`

**Observed:** Most section boundaries are whitespace or a hairline, not a change of fill.

**Transfer:** Let atmospheric media supply local color while the surrounding canvas remains uninterrupted.

#### Ruled band · level 0

**Use:** Statistics, proof, resources and comparison panels.

**CSS:** `border-left: 1px solid rgba(38,38,35,0.1); padding: 0px 8.1px; box-shadow: none`

**Observed:** Adjacent columns share the reading canvas; the last column closes the band with a right rule. No radius or floating-card shadow.

**Transfer:** Use a tall open frame with a topic at the top, useful content in the middle and an index at the foot.

#### Dark closing field · level 0

**Use:** Shared final destination.

**CSS:** `background: #1a1a1a; color: #f0f0ee`

**Observed:** A long, dense navigation system follows a short sales invitation; the wordmark is lower contrast than the links.

**Transfer:** Reserve the charcoal reversal for an emphatic end rather than alternating dark and light at every chapter.

#### Progressive navigation blur

**Use:** Soft transition behind the fixed header.

**CSS:** `backdrop-filter: blur(8px)`

**Observed:** Masked overlapping layers use 4px, 8px, 16px, 32px and 64px backdrop blur over a 117px-deep area, fading toward the body.

**Transfer:** Use a progressive masked blur so content passing behind the nav softens without turning the bar into an opaque slab.

#### Editorial enclosure · level 1

**Only for:** company stories and partner walls

**Use:** Bounded media cards rather than the default open bands.

**CSS:** `background: #f8f8f7; border: 1px solid rgba(0,0,0,0.1); border-radius: 4px; overflow: hidden`

**Observed:** Partner marks are centered with ample interior air; news cards put a colorful image above text.

**Transfer:** Keep the enclosure thin and the radius almost square.

## Components

### Fixed navigation

**Use:** Persistent compact site navigation.

**CSS:** `position: fixed; height: 64px; z-index: 10; width: 100%`

**Text style:** `navigation` — Suisse Intl 400 · 11.7px/20px

**Observed:** Small identity at the left of the centered main container, drawer triggers alongside it, three utility links at the far right; Progressive navigation blur lies behind the text. On charcoal, the identity and links reverse to light.

**Transfer:** Keep the navigation visually smaller than the media, with no enclosing pill or conversion banner.

### Primary button

**Use:** Main conversion in a paired action group.

**CSS:** `background: #1a1a1a; color: #f8f8f7; border-radius: 3.6px; padding: 0px 10.8px; height: 29px; display: flex; align-items: center; justify-content: center`

**Text style:** `button` — Suisse Intl 450 · 11.7px/1

**Observed:** Smoothened rectangular corners; default label produces a roughly 95px width. Dedicated product pages use black rather than charcoal. It sits beside a pale action with a 5.4px gap.

**States:** Declared: hover background #353535; active scale 0.97. Dedicated product variant: hover and focus-visible background #2a2a2a.

**Transfer:** Keep labels short and widths content-driven.

### Secondary button

**Use:** Developer or lower-commitment alternative beside the primary action.

**CSS:** `background: #f0f0ee; color: #1a1a1a; border-radius: 3.6px; height: 29px; padding: 0px 10.8px; display: flex; align-items: center; justify-content: center`

**Text style:** `button` — Suisse Intl 450 · 11.7px/1

**Observed:** Shares the primary button's geometry, without an outline. A documentation label is another variant of the same construction.

**States:** Declared: hover background #deded9; active scale 0.97. Documentation variant: hover and focus-visible opacity 0.7.

### Directional text link

**Use:** Capability-level exploration and grouped related destinations.

**CSS:** `color: #1a1a1a; position: relative; text-align: right`

**Text style:** `text-link` — Suisse Intl 400 · 18px/1.4 · tracking -0.03em

**Observed:** Unboxed link stacks align to the right edge of a capability row. Directional arrows belong to the link treatment, not to round icon badges.

**States:** Declared: hover color #1a1a1a.

### Metric panel

**Use:** Quantified proof without a card-heavy appearance.

**CSS:** `border-left: 1px solid rgba(38,38,35,0.1); padding: 0px 8.1px; display: flex; flex-direction: column; justify-content: space-between; row-gap: 21.6px; height: 461px`

**Text style:** `heading` — Suisse Intl 400 · 32.4px/1.22 · tracking -0.03em

**Observed:** Caption topic at top, large metric and tiny explanation around the vertical middle, index at bottom. Four panels typically share a single band.

**Transfer:** Use a meaningful metric plus a concise qualifier; keep the numeral regular weight.

### Glow proof panel

**Use:** Customer outcome and quotation.

**CSS:** `border-left: 1px solid rgba(38,38,35,0.1); padding: 0px 8.1px; position: relative; height: 461px; display: flex; flex-direction: column; justify-content: space-between`

**Text style:** `caption` — Suisse Intl 400 · 9px/1.3

**Observed:** Two panels are visible across the main frame, with partner mark above a middle-aligned outcome, quotation and attribution; a narrow colored light spills inward at the outer edge. Arrow controls sit by the section heading.

**Transfer:** Let the measured outcome lead; quotations are subordinate to it, not giant pull quotes.

### Footer column

**Use:** Navigation, legal and getting-started groups in the dark ending.

**CSS:** `border-left: 1px solid rgba(243,243,245,0.06); padding: 0px 8.1px; display: flex; flex-direction: column`

**Text style:** `footer-link` — Suisse Intl 400 · 11.7px/1.8

**Observed:** Small muted label at the head, link groups separated by 18px, substantial vertical space before the links and tiny index at the foot. Six columns form a 622px-high desktop band.

### Sales invitation

**Use:** First action in the dark ending.

**CSS:** `color: #f0f0ee`

**Text style:** `heading` — Suisse Intl 400 · 32.4px/1.22 · tracking -0.03em

**Observed:** A large plain text link followed by a thin right arrow; no filled button, border or surrounding card.

### News card

**Only for:** editorial sections

**Use:** Recent stories or announcements.

**CSS:** `background: #f8f8f7; border: 1px solid rgba(0,0,0,0.1); border-radius: 4px; display: flex; flex-direction: column; overflow: hidden`

**Text style:** `news-title` — Suisse Intl 400 · 21.6px/1.33 · tracking -0.03em

**Observed:** Graphic image first, with small category and reading-time labels overlaying its upper edge; multi-line title and date below with 21.6px content padding. Featured cards are wider than the three-up secondary stories.

**States:** Declared: hover background #ffffff; border remains 1px solid rgba(0,0,0,0.1).

### Person row

**Only for:** company people directories

**Use:** Compact human directory.

**CSS:** `background: #f8f8f7; border-radius: 12px; padding: 12px; display: flex; align-items: center; gap: 12px`

**Text style:** `person-name` — Suisse Intl 400 · 14px/1.5

**Observed:** 36px circular headshot beside two lines for name and muted role; four columns of stacked entries rather than large portrait cards.

**States:** Declared: hover background #ffffff.

### Partner tile

**Only for:** company partner narratives

**Use:** Institutional backing or ecosystem partners.

**CSS:** `border: 1px solid rgba(0,0,0,0.1); border-radius: 4px; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden`

**Observed:** Centered partner identity; featured tiles span the right-hand column and include a small relationship label and URL near the lower left. Smaller tiles form a two-column wall beneath them.

**Transfer:** Vary tile importance by span and space, not exaggerated border weight.

## Imagery and graphics

### Atmospheric interface vignettes

**Use:** Signature opening constellation, capability illustrations and resource tiles.

**Observed:** Small, legible interface panes float over richly tinted, directional organic textures: windswept green grass, cyan water or cloud, rose translucent folds, ochre light and blue air. Rounded-looking perimeters are heavily feathered into the off-white page, while the central controls remain crisp. Opening scenes are roughly 267–288px square and capability scenes 324px square; some panes look frosted and others use a white phone cropped at its bottom.

**Transfer:** Recompose the new product's real interface as one concise pane per scene. At minimum, make a convincing simplified control group, one dominant colored textured backing, and a soft masked edge; preserve readability in the center rather than blurring the entire object.

**Build:** Place a square directional-texture layer behind a crisp UI pane. For an artwork-free version, combine a colored radial wash with diagonal translucent streaks in SVG, add subtle turbulent displacement to the streaks, and mask the square with a broad opaque center fading to transparency at the perimeter. Use rgba(255,255,255,0.18) for glass panes with a faint white edge and backdrop blur; keep the outer texture softness separate from UI text. Reuse this treatment at small square and wide landscape scales.

### Proof edge light

**Use:** Signature luminous accents on restrained customer proof.

**Observed:** Cyan and blue light is visible as a slender vertical spill at a panel's outer edge, fading to white before reaching most text. The underlying circles are 288px wide with 64px blur; the blue has opacity 0.8.

**Transfer:** Keep the effect peripheral and clipped, so it animates an otherwise neutral proof band without becoming a gradient card.

**Build:** Position a 288px circle at the right edge of each 461px panel near its vertical center. Fill with #00a2c7 or #0052ff, apply blur(64px), and clip almost all of the circle outside the panel. Fade the clipping boundary with an SVG mask; layer the rule and text above it. Use opacity 0.8 on blue.

### Monumental tonal wordmark

**Use:** Required typographic sign-off within the dark ending.

**Observed:** A lowercase identity nearly fills a 1098×236px artwork area. Its dark-on-dark treatment is much lower contrast than nearby navigation; it is a visual mass rather than another headline.

**Transfer:** Set the new identity as an SVG wordmark or tightly fitted grotesk lettering. If no wordmark exists, use the product's name with adjusted spacing to fill the same wide, shallow proportion.

**Build:** Fit SVG text or outlined lettering to a wide shallow viewBox, preserving the identity's proportions. Place it on #1a1a1a with a subtly lighter charcoal fill using rgba(255,255,255,0.04) as a starting treatment; make it subordinate to the light sales invitation. Keep 66.6px before the small disclosure row.

### Landscape manifesto

**Only for:** company and purpose pages

**Use:** Immersive image-led opening.

**Observed:** An edge-to-edge 1440×800px grassy volcanic landscape under a pale overcast sky. Small white words are scattered across the terrain rather than typeset as a conventional centered headline. Faint geometric grid fragments overlay the photograph.

**Transfer:** Choose one expansive, unpeopled landscape with a low-noise sky and textured foreground; distribute a short purpose statement among regions of the image.

**Build:** Use a full-bleed landscape photograph with cover fitting. Add an SVG overlay of thin rgba(255,255,255,0.12) orthogonal lines: broad rectangular cells and a few denser grid clusters. Place short white word groups across alternating heights, leaving the center open.

### Industry media ribbon

**Only for:** industry longform pages

**Use:** Product immersion beneath the split opening.

**Observed:** Three horizontally overflowing 619×439px media panels with violet directional textures, feathered edges, black phone hardware and compact black notification UI. The center panel is fully visible while neighboring panels extend offscreen.

**Transfer:** Use a coherent application-specific color family across the ribbon; show complementary product moments rather than repeating one identical image.

### Wide operational scene

**Only for:** deep product chapters

**Use:** Major conceptual illustration between quieter text and ruled proof sections.

**Observed:** A 1192×670px blue, diagonally streaked cloud field backs two translucent interface panes joined by a thin white connector with dot terminals. The entire scene feathers into the canvas while the two controls remain legible.

**Transfer:** Show a real relationship between two product objects; use the interface-vignette construction at landscape scale and a single thin connector rather than a dense flowchart.

**Build:** Extend the atmospheric texture to a 1192×670px field. Place two unequal glass panels near the middle, one slightly higher than the other; connect their nearest edges with an SVG path using a soft elbow, a 1px white stroke and small filled endpoint circles. Mask the perimeter with a broad fade.

### Icons

**Observed:** Navigation arrows and carousel chevrons are thin, unboxed and charcoal. Carousel SVGs occupy 24×24px with 0.9px round-capped strokes. Small category symbols and vivid semantic colors remain primarily inside product illustrations and tables.

**Transfer:** Use minimal line arrows for marketing navigation; keep colorful category icons inside explanatory UI rather than attaching a colored icon badge to every marketing heading.

## Section recipes

How recurring sections are built.

### First screen: Constellation opening

**Observed:** A 900px off-white stage puts Fixed navigation above a constellation of feathered interface vignettes. The back layer is the Reading canvas, then rich softly bounded scenes around the perimeter, then a clear central text pocket above them. The regular 43.2px headline occupies about a quarter of the viewport width; its stack is constrained to 522px, with an approximately two-line 11.7px gray support statement and paired 29px Primary button and Secondary button beneath. Around the stack, imagery appears in top, side and bottom clusters, several clipped by the viewport. All headline, support, actions and the surrounding product objects are visible in the first 900px; partner proof and the explanatory statement follow below the fold.

**Transfer:** Make a perimeter constellation of different useful moments from the new product, not generic icons. Without finished media, use simplified crisp UI panes over directional textured washes with feathered edges. Dedicated product and industry pages instead open with a left-aligned display headline and small right-aligned support/actions in a spacious split row, followed by a wide scene or media ribbon. Company pages use the Landscape manifesto variant.

**Avoid:** Do not replace the center pocket with a giant headline, a dashboard filling the entire stage, a conventional left-text/right-device split or hard-edged colorful tiles.

**Text style:** `display` — Suisse Intl 400 · 43.2px/1.15 · tracking -0.04em

### Quiet explanatory statement

**Observed:** A 549px-wide paragraph sits near the center of a 461px open band. The first sentence is charcoal and the continuation gray, both in the statement recipe and inline rather than separate title/body elements.

**Transfer:** Introduce the product's premise or challenge in one readable paragraph; distinguish claim from explanation through color rather than scale.

**Text style:** `statement` — Suisse Intl 400 · 18px/1.3 · tracking -0.03em

### Ruled quantified proof

**Observed:** A four-column Ruled band uses Metric panel components. Topic labels are at the top, regular large figures around the middle, tiny explanatory lines immediately beneath, and indices at the bottom. The whole band is 461px tall.

**Transfer:** Choose a few credible measures of value, reach or reliability; maintain the tall empty areas and delicate rules.

### Numbered capability stage

**Observed:** A 32.4px section title receives 72px above and below. Each following 456px row begins with a tiny index and hairline; small body-scale heading and support occupy the left quarter, a 324px Atmospheric interface vignette anchors the central area, and Directional text links align to the far right.

**Transfer:** Give each capability a distinct visual object and concise supporting explanation. Keep related links in a plain vertical stack rather than a set of buttons.

**Text style:** `heading` — Suisse Intl 400 · 32.4px/1.22 · tracking -0.03em

### Luminous customer proof

**Observed:** A section heading and two unboxed chevrons introduce adjacent Glow proof panels. Partner identity, large measured outcome, compact quotation and tiny attribution sit within vertical rules; Proof edge light grazes each panel boundary. A subdued horizontal partner-logo row sits below.

**Transfer:** Make proof concrete and readable without expanding the quotation into a testimonial billboard.

### Resource band

**Observed:** A top hairline and heading share a row with paired actions. Four tall ruled panels place small labels at top, feathered interface artwork in the middle and indices below, using the same band grammar as metrics.

**Transfer:** Offer distinct ways into the product, such as a guide, sandbox, example and builder, using actual entry-point previews.

### Dark destination ending

**Observed:** Dark closing field begins with 115.2px of top space and Sales invitation. Footer columns follow after another 115.2px; their indices align along the bottom. The Monumental tonal wordmark follows with a further 115.2px separation, then a small disclosure row 66.6px later. The desktop ending occupies roughly 1408px in total.

**Transfer:** Retain the sales invitation, ruled navigational architecture and low-contrast identity artwork on every page; adapt the categories and disclosure to the new product rather than shortening the close into a small utility bar.

### Editorial directory and story wall

**Only for:** company pages

**Observed:** Small editorial-label titles sit on black bottom rules. A narrow stacked manifesto precedes two-column explanatory copy; Person rows form a four-column directory. A sticky 24px narrative faces a partner wall, and News cards form two featured columns above three smaller stories. A jobs module follows before the shared dark ending.

**Transfer:** Use this denser editorial language for people, institutional proof and updates, not for ordinary product capability rows.

**Text style:** `editorial-label` — Suisse Intl 450 · 14px/1.42

### Rail-based product argument

**Only for:** industry longform pages

**Observed:** Industry media ribbon leads into a 2:4:2 grid with sticky left contents and a 468px reading column. Chapters have 72px gaps, 18px two-tone lead sentences, 11.7px/1.6 paragraphs, lightweight ruled tables and a code example. The last chapter closes with a compact action pair before the dark ending.

**Transfer:** Develop a specific audience's problem, product model, economic value, trust, integration and future use through readable chapters rather than a wall of cards.

**Text style:** `longform-body` — Suisse Intl 400 · 11.7px/1.6

### Product economics and control proof

**Only for:** deep product pages

**Observed:** A two-column ruled band contrasts one 32.4px outcome with a small list of economic mechanisms. A wide operational scene introduces a further concept; paired diagrams compare approaches, followed by a three-column, two-row grid of small benefits.

**Transfer:** When the product needs deeper explanation, separate the measurable result, conceptual illustration and operational evidence into distinct visual scales.

### Centered final promise

**Only for:** deep product pages

**Observed:** A centered 540px statement sits in a 461px open band; its main promise is dark, the short concluding line muted. Paired compact actions follow with about 28.8px separation.

**Transfer:** Conclude the product-specific argument in a modest paragraph before moving into the shared closing system.

**Text style:** `statement` — Suisse Intl 400 · 18px/1.3 · tracking -0.03em

## Page flow

**Storyline:** Promise → tangible product world → concise explanation → measured proof → capability chapters → validation and entry points → shared dark destination; depth and order adapt to purpose.

### Broad marketing landing page

1. **Promise** — Centered headline and paired actions inside an atmospheric interface constellation.
2. **Social proof** — Subdued partner marks followed by a narrow two-tone explanatory paragraph.
3. **Quantified proof** — Four tall ruled metric panels.
4. **Capability chapters** — Numbered rows with small left copy, central interface object and right-aligned destinations.
5. **Validation** — Luminous outcome-and-quotation panels plus partner marks.
6. **Entry points** — Four ruled resource previews and repeated conversion pair.
7. **Closing call** — Large sales text link, six ruled footer columns, tonal wordmark and disclosure.

**Transfer:** Use this as the default new landing-page grammar: visual breadth first, then an increasingly concrete explanation and ways to start.

### Company credibility and purpose

1. **Purpose** — Full-bleed landscape with dispersed statement words and faint grid geometry.
2. **Manifesto** — Huge narrow stacked title with restrained two-column explanation.
3. **Human proof** — Compact portrait-and-role directory beneath a black ruled label.
4. **Institutional proof** — Sticky narrative facing featured and small partner tiles.
5. **Current activity** — Two featured stories, three supporting stories and a roles module.
6. **Closing call** — Shared sales invitation, ruled navigation and tonal wordmark.

**Transfer:** Use editorial sections to make the institution credible; preserve the same ending rather than inventing a separate company-page identity.

### Audience-specific longform argument

1. **Audience promise** — Split opening with short left headline and right support/action pair.
2. **Product immersion** — Violet interface ribbon overflowing both edges.
3. **Problem and solution** — Sticky contents rail beside narrow chapters with two-tone leads.
4. **Value and trust** — Lightweight economics and permission tables.
5. **Integration proof** — Code example and concise implementation explanation.
6. **Future relevance** — Specific advanced use case with an atmospheric interface scene.
7. **Closing call** — Short concluding argument, paired actions, then the shared dark destination.

**Transfer:** Keep the argument specific to one audience and use a stable contents rail for depth instead of repeating large hero modules.

### Deep product landing page

1. **Product promise** — Split headline/support opening with compact actions above a wide animated product world.
2. **Problem framing** — Narrow two-tone paragraph and four quantified proof columns.
3. **Capability chapters** — Repeated numbered capability stages.
4. **Economic proof** — Two ruled columns connect an outcome to revenue mechanisms.
5. **Concept demonstration** — Large atmospheric linked-interface scene and explanatory statement.
6. **Operational proof** — Paired comparison diagrams, another statement and a six-item ruled grid.
7. **Closing call** — Centered promise and paired actions, then shared sales invitation, footer architecture and wordmark.

**Transfer:** Extend the default language with conceptual scenes and diagrams only where they resolve an important product question.

## Writing

Direct, commercially literate and technically grounded. Confidence comes from concrete operations, ownership and consequences, not exuberant adjectives; warmth comes from describing what people and businesses gain.

**Do not copy:** Do not reuse Lightspark names, identity artwork, named partners, customer quotes, proprietary product names, financial claims, coverage figures, revenue figures or compliance claims. All examples illustrate structure and must be replaced with truthful content for the new product.

- **Addressing the reader:** Address the buyer as you and your; describe the buyer's users as your customers or your users. Refer to the product by name when defining its role, using we sparingly for institutional statements.
- **Rhythm:** Short sentence-case headlines, compact action labels and occasional sequences of clipped sentences. Pair a crisp assertion with a more explanatory continuation; longform pages alternate short lead lines with tightly edited paragraphs.

| Role | Pattern | Typical length | Examples of the pattern |
| --- | --- | --- | --- |
| Hero headline | Name the category or the audience plainly rather than using an elaborate metaphor. | 3–7 words | “The API for money”<br>“Global accounts” |
| Supporting line | List concrete capabilities, then link them to ownership or an economic result. | 1–3 short sentences | “Launch global accounts, payments, cards, stablecoins, and more. All of it under your brand, with your economics.” |
| Contrast lead | A dark premise followed by a muted tension or consequence. | Two short sentences | “The platform creates the income. But someone else gets the account.” |
| Technical benefit | State a concrete control in a memorable short contrast. | 4–12 words | “The agent gets a pocket. Not the keys.” |
| Primary action | Plain verb plus useful object, without cleverness. | 2–4 words | “Book a demo”<br>“Get API key”<br>“Talk with sales” |

**Words and phrasing to use:** your brand; one integration; send, receive, hold, spend; open; instant; global; permissions; economics; build; live in days

**Avoid:** revolutionary magic; seamless synergy; game-changing; unleash limitless potential; exclamation-heavy promises; vague AI superlatives

**Rules:**

- Tie an abstract infrastructure claim to a visible operation or practical outcome.
- Use parallel verbs for breadth, then a short sentence for the payoff.
- Keep captions descriptive and topic labels brief; reserve detail for the narrow longform column.
- Use numerals with qualifiers where proof is real; distinguish the result from the mechanism that produces it.

## Do's and Don'ts

### Do

- Keep default display type at 43.2px, weight 400 and -0.04em tracking at the desktop reference width.
- Let the 1098px frame govern text, proof and footer alignment while wide media extends to 1192px.
- Use 1px translucent vertical rules and 8.1px insets to organize proof without enclosing every panel.
- Maintain 29px control height and 3.6px corners for conversion pairs.
- Separate the crisp center of product UI from a soft, feathered textured perimeter.
- Repeat tiny 7.7px two-digit indices as navigational markings, not giant decorative numbers.
- Keep supporting statements to a roughly 549px measure and body-scale descriptions to compact columns.
- Include both the peripheral proof glow and the wide tonal identity sign-off in the visual vocabulary.

### Don't

- Do not use heavy 700-weight display typography; the regular cut and tightened tracking carry the brand's confidence.
- Do not turn the primary CTA into a 56px pill; its miniature rectangular scale is intentional.
- Do not tint the entire reading canvas cyan or violet to match a product scene.
- Do not add elevated drop shadows to ruled metric and resource panels; their structure is flat.
- Do not enlarge 9px annotations into bold uppercase section banners.
- Do not convert right-aligned capability link stacks into colored icon cards.
- Do not use equally saturated text, rules and media; keep marketing typography neutral and let the objects hold color.
- Do not make the ending's identity artwork bright white or more prominent than the sales link.

## Motion and responsive

### Motion

**Observed:**

- Opening media declares independent wandering animations on horizontal and vertical axes: 12s and 16s, cubic-bezier(.455,.03,.515,.955), infinite.
- Default opening buttons declare background-color 0.15s and scale 0.15s transitions; active scale is 0.97.
- Text and footer links declare opacity 0.2s and font-variation-settings 0.3s cubic-bezier(0.175,0.885,0.32,1.1); header links declare color 0.25s.
- Proof glows declare transform 0.6s cubic-bezier(0.175,0.885,0.32,1.1).

**Transfer:**

- Let the opening objects drift independently around the fixed reading pocket rather than moving the headline.
- Use subtle control compression and short color changes; keep glow movement peripheral to text.

**Unknown:**

- Wander distances and the exact choreography of scroll-triggered appearances are not specified.
- Interactive product scene sequences and reduced-motion behavior are not established.

### Responsive

**Observed:**

- Declared width thresholds include 376px, 480px, 719px, 720px, 768px, 959px, 960px, 1023px and 1200px; additional page-specific thresholds occur.
- Headline, statement, heading and major spacing sizes use clamp formulas.

**Transfer:**

- On narrow layouts, protect the clear hero text pocket by reducing the number of simultaneously visible peripheral objects rather than shrinking the interface panes into illegible thumbnails.
- Allow ruled bands and the six-column ending to reflow while keeping labels, main content and indices in their original hierarchy.
- For longform, move the contents rail out of the reading column's way rather than squeezing the 468px desktop measure between two rails.

**Unknown:**

- Exact mobile column counts, navigation replacement and artwork arrangement are not established; these are adaptation guidance rather than a verified mobile layout.

## How to use this guide

1. Start from the Essentials and the first-screen recipe; where the guide offers variants, use the default named for a new marketing page.
2. Plan the page before building: map your content onto the section recipes and page flow, then check the plan against the Do's and Don'ts.
3. Build with the tokens and component specs; recreate signature graphics with their build recipes instead of generic decoration, and use the named font substitutes if a font is unavailable.
4. Render the page at desktop and mobile widths, compare it with the Essentials and the Don'ts, and fix the differences before you finish.
