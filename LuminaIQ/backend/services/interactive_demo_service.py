"""
Interactive Demo Service — AI-Generated HTML Visualizations

Two-step pipeline:
  Step 1 (Prompt Enhancer): Takes a raw topic like "Newton's 3rd Law" and
         converts it into a rich, detailed 3D interactive scenario description.
  Step 2 (Code Generator): Takes that enhanced scenario and generates a
         complete self-contained HTML/CSS/JS page with 3D visuals.
"""

from services.llm_service import llm_service
from utils.logger import logger
import re

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1 — PROMPT ENHANCER
#  Converts a bare topic into a vivid 3D interactive visualization idea
# ═══════════════════════════════════════════════════════════════════════════

ENHANCER_SYSTEM_PROMPT = """You are an expert educational experience designer.

Given a learning **topic**, your job is to design a vivid, detailed,
interactive 3D visualization scenario that will help a student deeply
understand the concept through hands-on exploration.

## OUTPUT FORMAT
Return ONLY a single block of text (no markdown, no headings, no bullet
points) — a rich, detailed paragraph describing:

1. **What the user sees** — the 3D scene, objects, colors, environment
2. **What the user can interact with** — buttons, sliders, drag/click actions
3. **What happens when they interact** — animations, physics, cause-and-effect
4. **What they learn** — the educational takeaway made obvious through the visuals
5. **Real-world analogy** — a concrete physical example (rocket, bridge, pendulum, etc.)

## RULES
- Always think in terms of 3D scenes built with Three.js
- Make it physical/tangible — rockets that fly, balls that bounce, gears that turn
- Include at least 3 interactive controls (buttons, sliders, toggles)
- Describe specific colors, lighting, camera angles
- Keep it to ONE dense paragraph, max 200 words
- The description must be so detailed that a developer could build it directly

## EXAMPLES

Topic: "Newton's 3rd Law"
→ "A 3D outer-space scene with a dark starfield background. A detailed rocket
sits on a launch pad. When the user clicks 'LAUNCH', orange-yellow flame
particles burst from the engines downward (ACTION), and the rocket smoothly
accelerates upward (REACTION). A real-time force-arrow diagram shows equal
and opposite red/blue arrows. A slider controls thrust power — higher thrust
= bigger flames = faster ascent. A 'Zero Gravity' toggle removes the launch
pad and shows the rocket floating, demonstrating that the reaction still
works in space. Labels explain F_action = -F_reaction. The camera orbits
slowly around the scene."

Topic: "Binary Search"
→ "A 3D shelf of glowing numbered cubes arranged in sorted order. The user
types a target number. The algorithm highlights the middle cube in yellow,
compares, then the eliminated half fades to gray and shrinks. The remaining
half zooms in. Each step shows the comparison with floating text. A speed
slider controls animation pace. A 'Step' button lets the user advance
manually. A counter shows O(log n) comparisons vs the total array size."

Now design a scenario for the given topic."""


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 2 — CODE GENERATOR
#  Takes the enhanced scenario and generates complete HTML
# ═══════════════════════════════════════════════════════════════════════════

CODE_GEN_SYSTEM_PROMPT = """You are an elite interactive visualization engineer.
Your job is to take a detailed visualization scenario description and produce
a stunning, self-contained HTML page that implements it exactly.

## ABSOLUTE RULES

1. **Output ONLY a single, complete HTML document** — start with `<!DOCTYPE html>`
   and end with `</html>`.  No markdown fences, no explanation text before or after.

2. **Use Three.js for 3D** — Load via CDN:
   `<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>`
   Use the global `THREE` object. Do NOT use ES modules or `import` statements.
   For 2D physics, you may also use Matter.js via CDN.

3. **Visual excellence** — rich colors, gradients, smooth 60fps animations,
   particle effects, dynamic lighting, subtle shadows.  Dark-themed by default
   (dark background `#0a0a0f` to `#1a1a2e`, vivid accent colors).

4. **Interactivity** — implement ALL interactive controls described in the
   scenario: buttons, sliders, toggles, click-to-explore.  Every control must
   visibly affect the 3D scene.

5. **Educational** — add clear text labels, floating annotations, force arrows,
   legends, and a title/subtitle explaining the concept being visualized.

6. **Responsive** — works from 360px to 1920px.  Use `vw`/`vh`/`%`/`flex`/`grid`.

7. **Performance** — efficient requestAnimationFrame loops.  Target 60fps.

8. **UI overlay** — place control buttons/sliders in a semi-transparent glassmorphic
   panel overlaid on the 3D scene (position: fixed or absolute).  Use:
   - `rgba(255,255,255,0.08)` background with `backdrop-filter: blur(12px)`
   - Border radius `12px` for cards, `8px` for buttons
   - System fonts: `system-ui, -apple-system, 'Segoe UI', sans-serif`

## CRITICAL
- Implement the EXACT scenario described — every object, control, and interaction
- If the scenario mentions a rocket, BUILD a 3D rocket with geometry
- If it mentions force arrows, DRAW them with ArrowHelper or custom geometry
- If it mentions particles, CREATE a particle system
- Make the user say "WOW" when they see it

Remember: output ONLY the HTML.  Nothing else."""


def _extract_html(raw: str) -> str:
    """Extract clean HTML from LLM response, stripping markdown fences."""
    # Pattern 1: ```html ... ```
    match = re.search(r'```html\s*(<!DOCTYPE.*?</html>)\s*```', raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Pattern 2: ```...```
    match = re.search(r'```\s*(<!DOCTYPE.*?</html>)\s*```', raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Pattern 3: Raw HTML (no fences)
    match = re.search(r'(<!DOCTYPE.*?</html>)', raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Pattern 4: Starts with <html> (no doctype)
    match = re.search(r'(<html.*?</html>)', raw, re.DOTALL | re.IGNORECASE)
    if match:
        return '<!DOCTYPE html>\n' + match.group(1).strip()

    # Fallback
    logger.warning("[InteractiveDemo] Could not extract clean HTML — returning raw response")
    return raw.strip()


class InteractiveDemoService:
    """Two-step pipeline: topic → enhanced 3D scenario → HTML code."""

    async def _enhance_topic_to_scenario(
        self,
        topic: str,
        additional_info: str = "",
    ) -> str:
        """
        Step 1: Convert a bare topic into a rich 3D interactive scenario.
        Returns a detailed paragraph describing the visualization.
        """
        user_parts = [f"Topic: \"{topic}\""]

        if additional_info:
            user_parts.append(f"Additional user instructions: {additional_info}")

        user_parts.append("Design the most impressive, educational, interactive 3D visualization scenario for this topic.")

        user_prompt = "\n".join(user_parts)

        logger.info(f"[InteractiveDemo] Step 1: Enhancing topic → 3D scenario: {topic}")

        messages = [
            {"role": "system", "content": ENHANCER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        scenario = await llm_service.chat_completion(
            messages=messages,
            temperature=0.9,  # creative
            max_tokens=500,   # keep it concise
        )

        # Clean up — strip any accidental markdown
        scenario = scenario.strip().strip('"').strip("'")
        logger.info(f"[InteractiveDemo] Step 1 done. Scenario: {scenario[:120]}...")

        return scenario

    async def generate_demo(
        self,
        topic: str,
        additional_info: str = "",
        context_topics: list[str] | None = None,
    ) -> dict:
        """
        Full pipeline:
          1. Enhance topic → detailed 3D scenario
          2. Generate HTML from scenario
        """
        # ── Step 1: Enhance topic into 3D scenario ──────────────────────
        scenario = await self._enhance_topic_to_scenario(topic, additional_info)

        # ── Step 2: Generate HTML from the enhanced scenario ────────────
        user_parts = [
            f"Build this interactive 3D visualization:\n\n{scenario}",
        ]

        if context_topics:
            related = ", ".join(context_topics[:10])
            user_parts.append(
                f"\nRelated topics in the user's study material: {related}. "
                f"You may reference connections to these topics where relevant."
            )

        user_parts.append(
            "\nImplement EVERY detail from the scenario above. "
            "Use Three.js for 3D rendering. Make the controls work. "
            "Make the user say WOW."
        )

        user_prompt = "\n".join(user_parts)

        logger.info(f"[InteractiveDemo] Step 2: Generating HTML code for: {topic}")

        messages = [
            {"role": "system", "content": CODE_GEN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        raw = await llm_service.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=8000,
        )

        html_code = _extract_html(raw)

        title = f"Interactive Demo: {topic}"
        description = scenario[:200]

        logger.info(
            f"[InteractiveDemo] Step 2 done. Generated {len(html_code)} chars of HTML for '{topic}'"
        )

        return {
            "html_code": html_code,
            "title": title,
            "description": description,
        }


interactive_demo_service = InteractiveDemoService()
