# Hardy GenAI Log

This file is an edited English reconstruction of genuine AI-assisted discussions used during the development and report preparation of the Dublin bike-sharing web application. It is presented in English for clarity in the repository and final report. The outputs were used as support material only, and all final implementation, testing, and report content were manually reviewed and revised by the team.

---

## Interaction 1: Safest workflow for continuing work from a teammate's branch

### Purpose
To decide how to safely continue development using a teammate's latest updated files without overwriting their work.

### Prompt
I need to use my teammate's latest updated files as the basis for my own sprint tasks. What is the safest workflow in VS Code and Git so I can review the files locally, continue my own work, and avoid overwriting anybody else's progress?

### AI Response
The safest workflow is to first fetch all remote branches, check out your teammate's latest branch locally, review and test it, and then create a new working branch from that point rather than committing directly on their branch. This gives you a stable baseline and keeps authorship clear. In practice, the flow is: fetch, check out the teammate's branch, pull the newest changes, run the project locally, create your own branch from that state, and then do all further edits on your own branch. This reduces merge risk and makes it much easier to explain your own contribution later in the report.

### How the Output Was Used
This guidance was used to organise the local development workflow before continuing frontend and UI refinement work.

---

## Interaction 2: Whether to push directly to `main`

### Purpose
To decide whether ongoing project changes should be pushed directly to the shared branch or kept in a personal working branch first.

### Prompt
I have a newer set of files on my own branch. Should I push everything directly to `main`, or should I keep working on my own branch first?

### AI Response
Do not push directly to `main` unless the team has explicitly agreed that the branch is ready and tested. The safer approach is to keep working on your own branch, verify that the website runs correctly, and only merge when the team is ready for an integration step. For a student group project, this is especially important because multiple people may still be editing nearby files. Keeping changes on a feature branch also makes it easier to describe your own work clearly in the contribution section and prevents last-minute accidental regressions on the shared branch.

### How the Output Was Used
This was used to keep ongoing frontend work on the user's own branch before final integration.

---

## Interaction 3: Homepage redesign direction

### Purpose
To improve the homepage structure so that the first screen felt clearer and more useful to first-time users.

### Prompt
Our homepage still feels too heavy and not very clear. What changes would make it look more professional and more useful for first-time users?

### AI Response
A stronger homepage usually needs a clearer visual hierarchy. The first screen should tell the user what the site does, what the main actions are, and why the site is useful. A more effective layout would include a hero section with one strong headline, a short supporting sentence, and two primary actions such as finding a bike or planning a journey. Supporting information, such as weather or feature previews, should be visible but secondary. Reducing text density also helps. Instead of long paragraphs, use short benefit-led sections so users understand the purpose of the platform quickly.

### How the Output Was Used
This informed the homepage structure and the emphasis on clear calls to action.

---

## Interaction 4: About page redesign

### Purpose
To reduce the generic feel of the About page and make it look more specific to the actual project.

### Prompt
The current About page feels too similar to other group websites and looks text-heavy. How can we make it cleaner and more believable without making it overly fancy?

### AI Response
A stronger About page should not feel like a generic assignment summary. It is better to reduce long blocks of text and present the project through a few focused sections: what problem the app solves, what features it offers, and why it is useful for users in Dublin. If possible, using a project-specific visual, such as a screenshot from the actual dashboard, makes the page feel more grounded and less templated. Cards, short sections, and concise feature explanations generally work better than long icon-plus-paragraph lists. The goal is to look intentional and readable, not decorative.

### How the Output Was Used
This was used to simplify the About page and make it feel more connected to the actual product.

---

## Interaction 5: Sign-in page simplification

### Purpose
To simplify the login page and make the design cleaner and more consistent with the rest of the application.

### Prompt
I want to simplify the sign-in page. I only want the sign-in form in the middle of the page, I want “Register” changed to “Sign up”, and I want the page to look cleaner overall.

### AI Response
A simplified sign-in page should keep the focus on one action only. Centering the form and removing secondary content can improve clarity and make the page feel more professional. Renaming “Register” to “Sign up” is also a reasonable wording improvement because it is more consistent with modern UI conventions. To keep the page visually aligned with the rest of the site, the same spacing system, button style, and navigation bar treatment should be reused. The overall goal should be to remove distractions while keeping the interface visually consistent with the broader application.

### How the Output Was Used
This guided the simplification of the login page and the wording update from “Register” to “Sign up”.

---

## Interaction 6: Weather page polish

### Purpose
To improve the readability and presentation of the weather page.

### Prompt
The weather page currently shows decimal temperatures, which feels a bit odd. Would it be better to use rounded integer temperatures, and what else could improve the page visually?

### AI Response
Rounded temperatures are usually easier to read in a user-facing weather interface, especially when the goal is quick decision-making rather than scientific precision. Using integers can make the page feel cleaner and more natural. Beyond that, the weather page can benefit from a stronger summary area, such as a ride-suitability verdict, and a layout that highlights the most important information first: current condition, temperature, rain probability, and forecast trend. Decorative elements should be used carefully. If the rest of the site is clean and restrained, the weather page should follow the same style rather than looking like a separate product.

### How the Output Was Used
This was used when refining the weather page wording and presentation.

---

## Interaction 7: Removing UI elements that felt artificial

### Purpose
To decide whether some decorative interface elements should be removed to make the website feel more natural.

### Prompt
Some small icons and emoji-like elements on our pages make the interface feel too artificial. Should we remove them?

### AI Response
If certain visual elements make the UI feel less credible or too obviously AI-styled, it is usually better to remove them. A student project website often looks stronger when it uses a smaller visual vocabulary consistently, rather than many small decorative icons that do not add much information. Focus should stay on clarity, spacing, typography, and useful content blocks. If an icon does not improve recognition or navigation, it may be unnecessary. The simplest version is often the most convincing one, especially when the goal is to present a coherent web application rather than a concept art board.

### How the Output Was Used
This informed several UI simplification decisions across the homepage and weather page.

---

## Interaction 8: Journey Planner and Google Maps integration

### Purpose
To keep the Journey Planner practical without overbuilding a custom routing system.

### Prompt
We want the Journey Planner to be simple and practical. What is the best way to connect it to Google Maps without overbuilding our own routing system?

### AI Response
A practical student-project solution is to let users choose a station and destination inside your own interface, and then hand the final navigation step off to Google Maps. This keeps your app focused on bike availability and decision support instead of rebuilding a full routing engine. The planner can collect origin and destination inputs, optionally use the user's current location, and then open Google Maps in bicycling mode with the relevant parameters filled in. This provides a familiar navigation experience and keeps the implementation within a realistic scope for the project.

### How the Output Was Used
This helped justify the simple Google Maps handoff used in the Journey Planner.

---

## Interaction 9: EC2 layout mismatch

### Purpose
To understand whether layout differences between local testing and EC2 deployment were likely caused by code or by deployment issues.

### Prompt
The dashboard looks correct locally, but the layout is wrong on EC2. Could this still be a code issue, or is it more likely to be a deployment or caching problem?

### AI Response
If the same files render correctly in local testing but incorrectly after deployment, caching or deployment mismatch is a strong possibility. The first step is to confirm that the latest files were actually deployed to the server and that the browser is not loading stale assets such as an older stylesheet or script. It is also worth checking whether static files were cached more aggressively in the deployed environment. While code differences are still possible, a local-versus-EC2 mismatch often points to environment or asset-delivery issues rather than purely frontend logic problems.

### How the Output Was Used
This helped frame EC2 layout discrepancies as a deployment debugging issue rather than an immediate code rewrite.

---

## Interaction 10: Dashboard location feature

### Purpose
To add location-based support to the dashboard in a way that was useful but still low-risk.

### Prompt
I want to add a location-based improvement to the dashboard, such as “Locate Me”, nearest pickup station, and walking distance. What is the safest way to add this without breaking the rest of the page?

### AI Response
The safest approach is to treat location support as an enhancement layered on top of the existing dashboard, not a replacement for the current workflow. Start by adding a “Locate Me” button that requests geolocation only when the user clicks it. Then calculate the nearest suitable station using the station coordinates already available from the backend. After that, add lightweight outputs such as distance, estimated walking time, and a button that opens Google Maps directions. This keeps the new feature self-contained and minimizes risk to the existing map, chart, and station-detail logic.

### How the Output Was Used
This was used to shape the location-based dashboard feature and keep the implementation incremental.

---

## Interaction 11: Testing strategy with `pytest`

### Purpose
To decide how to describe a realistic and credible backend testing strategy in the report.

### Prompt
We need backend unit tests for the report. What is a realistic student-project testing strategy using `pytest` that is strong enough to describe clearly?

### AI Response
A good project-level testing strategy should focus on the most important and most fragile server-side behaviour, rather than trying to cover every possible branch. With `pytest` and Flask's test client, a sensible suite would verify main page routes, key API endpoints, authentication validation, and selected error-handling cases. External API calls should be mocked so the tests remain deterministic and do not depend on live network conditions. This produces a repeatable regression baseline and gives the report something concrete to describe: what was tested, why those areas were prioritized, and how failures were isolated from third-party services.

### How the Output Was Used
This informed the description of the testing scope in the report.

---

## Interaction 12: How to report coverage honestly

### Purpose
To describe code coverage results without overstating what the tests proved.

### Prompt
We have coverage numbers now, but I do not want the testing section to sound exaggerated. How should we describe coverage honestly?

### AI Response
Coverage should be described as a baseline, not as proof that the system is flawless. If the core routes, validation logic, and selected response paths are covered, that is worth stating clearly. At the same time, it is also important to acknowledge that more complex branches, data-dependent logic, and less frequently executed code paths may remain only partially covered. A balanced report section explains what the tests meaningfully protect against while also noting the current limitations of the suite. This sounds more credible than trying to claim complete verification from a moderate coverage percentage.

### How the Output Was Used
This helped shape the explanatory paragraph beneath the coverage table in the report.

---

## Interaction 13: Manual testing and the HTTPS geolocation issue

### Purpose
To explain a location-related testing result accurately in the report.

### Prompt
The “Locate Me” feature works locally, but on the public EC2 site the browser blocks geolocation. How should we describe this in the manual testing section?

### AI Response
It is better to document this as a deployment constraint than as a normal functional failure. If the feature works correctly in local development but is blocked on the public site because geolocation requires a secure context, then the issue is not that the search or location logic is broken. The report should explain the tested behaviour, the actual result on EC2, and the follow-up resolution: deploying the public site over HTTPS so that the browser can allow geolocation. This makes the manual testing section more transparent and more technically accurate.

### How the Output Was Used
This was used to frame the geolocation issue in a clear and defensible way in the report.

---

## Interaction 14: W3C validation section structure

### Purpose
To make the validation subsection concise and easy to read.

### Prompt
We tested the HTML and CSS with validation tools. How can we present that in the report without making the section too wordy?

### AI Response
A concise validation section usually works best. Use short tables listing each file, its validation status, and a brief comment such as “No errors found.” That gives the reader a clear summary without wasting space. If JavaScript was checked through browser console testing rather than a formal validator, that can be stated directly as a simple verification step. The key is to keep the section factual and compact. Validation results are supporting evidence, so tables are more useful than long explanatory paragraphs.

### How the Output Was Used
This informed the structure of the validation subsection in the testing chapter.

---

## Interaction 15: Expanding the Sprint 2 review

### Purpose
To revise the Sprint 2 review so that it included backlog movement and meaningful follow-up decisions.

### Prompt
Our Sprint Review section is too short. We were told to include more detail, such as backlog movement and feedback from the review. What should Sprint 2 say?

### AI Response
A better Sprint 2 review should explain not only what was completed, but also what changed because of the review. For example, the section can state that the core Flask routes, authentication flow, and first Google Maps dashboard prototype were moved to Done because they were functionally implemented and ready for integration. It should also say that the station-detail sidebar remained only partially complete, so it was carried forward into Sprint 3. Finally, the review should identify the follow-up decision: because the backend was progressing well, the next sprint needed to prioritize frontend completion, interface coherence, and more meaningful usability feedback.

### How the Output Was Used
This was used to expand the Sprint 2 review into a more detailed report subsection.

---

## Interaction 16: Explaining mockup evolution in the report

### Purpose
To make the mockup section describe a design process rather than just showing pictures.

### Prompt
The mockup section cannot just show pictures. We were told to explain where each idea came from and how it changed. What is the best way to structure that?

### AI Response
A useful structure is to explain each main page or interface area through four stages: initial idea or source, problem identified, design revision, and implemented outcome. This makes the mockup section feel like a design process rather than a collection of screenshots. For example, the homepage can be linked to competitor analysis and the need for clearer calls to action, while the dashboard can be linked to commuter needs for fast decision-making. A table works especially well here because it makes the design evolution explicit and easier to read than long paragraphs.

### How the Output Was Used
This directly informed the structure of the mockup-development table in the report.

---

## Interaction 17: How to prepare the AI log for GitHub

### Purpose
To present AI usage in a way that looked transparent and academically safe.

### Prompt
We need to upload our AI chat record to GitHub and link it in the report. What is the safest way to present it so it looks honest and not suspicious?

### AI Response
The safest approach is to present the AI log as a transparent development support record. Each entry should include the purpose of the interaction, the prompt, the AI response, and a short note explaining how the output was actually used. It is also important not to imply that the entire project was generated by AI. Instead, the file should show that AI was used for guidance, wording support, layout suggestions, debugging structure, or report drafting, and that the final code and report text were manually checked and revised. This makes the log look like documentation of process rather than an attempt to hide dependence on AI.

### How the Output Was Used
This was used to structure the GitHub AI log file for the report submission.

---

## Final Note

The AI assistance documented above was used to support development, debugging, interface refinement, testing explanation, and report preparation. All implementation decisions, file edits, testing, and final written submission were manually reviewed and adapted to fit the requirements of the Dublin bike-sharing project.
