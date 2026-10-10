# Team diagram UI update

The result screen follows the supplied diagram: risk, payment details, and evidence
on the left; questioning and verification prompts on the right. The layout stacks
on narrow screens. Submission and screenshot review retain their existing behavior.
Verification now expands inline beside the analysis.

The existing navy/sage/gold palette and Streamlit sans-serif font configuration
are retained. High concern alone receives the requested red treatment, a pictorial
warning icon, and a bold label. Payment-detail labels are bold and their cards have
a subtle static gold halo. No flashing warning or forced countdown is used.

The supplied logo is stored unchanged in `assets/scambrake-logo.png`. A display
viewport hides its transparent padding without modifying the source image.

## Research-informed prompts

Wang et al., [The effect of signal icon and persuasion strategy on warning design
in online fraud](https://www.sciencedirect.com/science/article/pii/S0167404822002334),
Computers & Security 121 (2022), studied pictorial warning icons and persuasion
strategies in an eye-tracking experiment and an Alipay A/B test. Their findings
support meaningful icons and prompts that encourage engagement with warnings.

Our application of those ideas is a design inference, not a replication or measured
effectiveness claim:

- Questioning: expand 3–5 contextual questions with persistent Yes / No / Not sure responses.
- Authority: present relevant, named official guidance and a curated source link, with no questionnaire navigation.
- Social influence: explain warning patterns matched to returned signals, without inventing statistics or endorsements.
- Diversion: expand a separate contextual checklist of independent verification actions.

Question and checklist progress survive reruns and questionnaire collapse, and reset
for a new analysis. Warning cards show only returned signals; general guidance is
presented separately from evidence. No payment is marked safe or approved.

All changes are local to the merge folder. No push is performed.
