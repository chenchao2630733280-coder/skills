# Product Contract

## Purpose

Model a general pet-owner chatbot that helps organize health information and simulate urgency-based routing. The product must support multi-symptom complaints rather than a small collection of fixed symptom flows.

## Supported surfaces

- Chatbot conversation
- Quick-reply chips
- Form-like cards inside chat
- Photo, video, report, and medication-package attachments
- Risk result card
- Veterinary handoff
- Follow-up tracking
- Shareable consultation summary

## Primary users

- Pet owners with limited medical vocabulary
- Owners managing multiple pets
- Owners who are anxious or uncertain about urgency
- Owners seeking routine care information
- Owners preparing information for a veterinarian

## Species scope

Treat cats and dogs as the detailed first-release scope. For rabbits, rodents, birds, reptiles, and other pets:

- provide only broad emergency screening;
- label species-specific uncertainty;
- recommend a veterinarian experienced with that species.

## General issue taxonomy

Recognize free text first, then map it to one or more categories:

- eating, drinking, and digestion;
- breathing and circulation;
- urination and reproduction;
- skin and coat;
- eyes, ears, and mouth;
- neurology and behavior;
- mobility, joints, and pain;
- ingestion, poisoning, and foreign bodies;
- trauma and accidents;
- preventive and daily care;
- test reports and medication records;
- postoperative, chronic-care, and recheck needs.

Do not force the owner to choose the correct category before they can describe the problem.

## Product states

| State | Purpose |
|---|---|
| `WELCOME` | Explain scope and offer entry points |
| `SELECT_PET` | Select or create the affected pet |
| `COLLECT_COMPLAINT` | Capture free-text complaint and attachments |
| `CONFIRM_EXTRACTED_ISSUES` | Let the owner correct extracted issues |
| `GLOBAL_EMERGENCY_SCREEN` | Check universal red flags |
| `CONTEXTUAL_EMERGENCY_SCREEN` | Check complaint-specific red flags |
| `DYNAMIC_INTERVIEW` | Ask the highest-value unanswered question |
| `CONFIRM_SUMMARY` | Confirm structured facts before guidance |
| `RISK_RESULT` | Present simulated action level and evidence |
| `FOLLOW_UP_TRACKING` | Track change over time |
| `HANDOFF` | Transfer to veterinarian or hospital |
| `CLOSED` | Save or finish the session |

## Minimum pet profile

Collect only what affects the current flow:

- name;
- species;
- approximate age or life stage;
- sex;
- weight if known;
- neuter status;
- pregnancy or lactation;
- chronic conditions;
- allergies;
- current long-term medication.

## Main interaction principles

- Free-text first, structure second.
- One decision-focused question per turn.
- Multiple symptoms remain in one combined session.
- Emergency routing interrupts ordinary flow.
- Normal findings should reduce repetition but must not produce false reassurance.
- The result explains why the product chose an action level.
- The owner can edit facts before the result.
- The owner can restart assessment when the pet's condition changes.
