# Visual assets

Six original AI-generated background scenes in a green and white visual palette inspired by the user's Sber style request. These are illustrative scenes, not photographs of actual Sber locations. Generated with OpenAI image generation and encoded as JPEG for web delivery:

- case-01.jpg: white business atrium with greenery.
- case-02.jpg: bright freelancer workspace.
- case-03.jpg: landscaped glass business campus.
- case-04.jpg: modern wellness reception.
- case-05.jpg: green logistics campus.
- case-06.jpg: glass meeting room and paperwork.

Six further original AI-generated cinematic environments for the visual novel episodes (`novel-01.jpg` through `novel-06.jpg`), one scene per case: component manufacturer office, delivery business workspace, retail headquarters meeting room, industrial HR/wellness lounge, logistics operations office, and technology finance workspace. Generated in one batch with OpenAI image generation; no characters, readable text, logos or interface elements. The EVE character is rendered separately from the supplied 3D model.

3D character: user-provided `aiprintgen_EVE Robot Character 3D Model-preview.glb`. The supplied head, torso and arm shells are separated into animated joints; original geometry and textures are retained. Arm axes are aligned to six explicit target directions, with a neutral arms-down pose. Cyan eye surfaces move with the gaze through a vertex shader. A small emerald tie mesh is attached to the torso. Meshopt decoder: three.js examples, MIT. Avatar poster rendered from the supplied model for devices without WebGL.

Three.js source: https://github.com/mrdoob/three.js (MIT).

Font: Manrope, Google Fonts, SIL Open Font License. Font family sources downloaded from https://fonts.googleapis.com/css2?family=Manrope:wght@200..800

Version 5 adds six original AI-generated episode environments: `env-desk.jpg` (analysis workstation), `env-call.jpg` (client contact space), `env-meeting.jpg` (meeting room), `env-hr.jpg` (HR lounge), `env-operations.jpg` (payments operations), and `env-campus.jpg` (business district). Four original fictional business character portraits, generated with transparent backgrounds, are served as `actor-finance.webp`, `actor-hr.webp`, `actor-accounting.webp`, and `actor-operations.webp`. They are illustrations, not portraits of real Sber employees. Generated with OpenAI image generation in a single batch and encoded for web delivery. Each episode selects a location and its cast from its authored scene context; the user-supplied EVE remains the mentor.

Arm shells now use principal-axis alignment and centred shoulder anchors for a straight neutral pose. The tie uses Sber green (#21A038), positioned lower on the torso.

Chapter headings: Oswald Bold, SIL Open Font License, used by the public Прожарка reference. Locally hosted Cyrillic and Latin subsets (`display-1.woff2`, `display-2.woff2`). License: `dist/assets/Oswald-OFL.txt`. Font source: https://github.com/google/fonts/tree/main/ofl/oswald .

Version 6 renames the mentor to «КМ» in the site interface; the original model filename remains recorded above for provenance. The eight new material icons are original inline SVG line drawings (wallet, team, document, launch, identity, shield, growth chart and satellites), authored for this site without external icon dependencies. Crossed ribbons and animated green text highlighting adopt the requested presentation techniques from the public Прожарка reference; its editorial content is not copied.
