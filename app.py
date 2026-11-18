"""
NHS Mental Health & Economic Inactivity Navigator with JARVIS AI Copilot
Free, open-source patient-facing platform.
Built by Gokul — github.com/Goku-coder336/mh-navigator
Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os, re, csv
from datetime import date
from typing import Dict, List, Any, Optional

# ─────────────────────────────────────────────────────────
# HELPER: FIND DATA FILE
# ─────────────────────────────────────────────────────────
def _find(name):
    """Find a data file whether it sits in data/ or next to app.py."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "data", name),
        os.path.join(here, name),
        os.path.join(os.path.dirname(here), "data", name),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(here, "data", name)


# ─────────────────────────────────────────────────────────
# SELF-CONTAINED 5-QUESTION MATCHING ENGINE
# ─────────────────────────────────────────────────────────
def load_organisations(path=None):
    if path is None:
        path = _find("organisations.csv")
    return pd.read_csv(path)


def match_organisations(df, condition, age, urgency, cost, format_pref):
    if urgency == "Tonight or this week":
        crisis = df[df["urgency_level"] == "immediate"]
        return crisis.head(3)

    results = df[df["urgency_level"] != "immediate"].copy()

    condition_map = {
        "Anxiety or panic": "anxiety",
        "Low mood or depression": "depression",
        "Trauma or PTSD": "trauma",
        "OCD or intrusive thoughts": "ocd",
        "Grief or bereavement": "grief",
        "Relationship difficulties": "relationships",
        "Eating difficulties": "eating",
        "I'm not sure": "general",
    }
    tag = condition_map.get(condition, "general")
    results = results[results["condition_tags"].str.contains(tag, na=False)]

    age_map = {
        "Under 18": "under 18",
        "18 to 25": "18 to 25",
        "26 to 64": "26 to 64",
        "65 and over": "65 and over",
    }
    age_tag = age_map.get(age, "")
    if age_tag:
        results = results[
            results["age_group"].str.contains(age_tag, na=False)
            | (results["age_group"] == "all ages")
        ]

    if cost == "Free only":
        results = results[results["cost_category"] == "free"]
    elif cost == "Up to £20 per session":
        results = results[results["cost_max"] <= 20]

    format_map = {
        "Online or video": "online",
        "Phone call": "phone",
        "Face to face": "in-person",
        "Text or chat": "text",
        "Something I can try on my own first": "online",
    }
    fmt = format_map.get(format_pref, "online")
    results = results[results["format_tags"].str.contains(fmt, na=False)]

    results = results.sort_values("speed_rank")
    return results.head(3)


# ─────────────────────────────────────────────────────────
# JARVIS AI CORE ENGINE
# ─────────────────────────────────────────────────────────
class JarvisEngine:
    CRISIS_KEYWORDS = [
        "suicide", "suicidal", "kill myself", "end my life", "want to die",
        "hang myself", "overdose", "slit", "jump", "can't go on", "cant go on",
        "better off dead", "end it all", "take my life", "self harm", "cutting myself"
    ]

    POSTCODE_TO_ICB = {
        "M": "NHS GREATER MANCHESTER INTEGRATED CARE BOARD",
        "BL": "NHS GREATER MANCHESTER INTEGRATED CARE BOARD",
        "OL": "NHS GREATER MANCHESTER INTEGRATED CARE BOARD",
        "SK": "NHS GREATER MANCHESTER INTEGRATED CARE BOARD",
        "WN": "NHS GREATER MANCHESTER INTEGRATED CARE BOARD",
        "NE": "NHS NORTH EAST AND NORTH CUMBRIA INTEGRATED CARE BOARD",
        "DH": "NHS NORTH EAST AND NORTH CUMBRIA INTEGRATED CARE BOARD",
        "SR": "NHS NORTH EAST AND NORTH CUMBRIA INTEGRATED CARE BOARD",
        "DL": "NHS NORTH EAST AND NORTH CUMBRIA INTEGRATED CARE BOARD",
        "CA": "NHS NORTH EAST AND NORTH CUMBRIA INTEGRATED CARE BOARD",
        "TD": "NHS NORTH EAST AND NORTH CUMBRIA INTEGRATED CARE BOARD",
        "L": "NHS CHESHIRE AND MERSEYSIDE INTEGRATED CARE BOARD",
        "CH": "NHS CHESHIRE AND MERSEYSIDE INTEGRATED CARE BOARD",
        "CW": "NHS CHESHIRE AND MERSEYSIDE INTEGRATED CARE BOARD",
        "WA": "NHS CHESHIRE AND MERSEYSIDE INTEGRATED CARE BOARD",
        "NW": "NHS NORTH WEST LONDON INTEGRATED CARE BOARD",
        "W": "NHS NORTH WEST LONDON INTEGRATED CARE BOARD",
        "HA": "NHS NORTH WEST LONDON INTEGRATED CARE BOARD",
        "UB": "NHS NORTH WEST LONDON INTEGRATED CARE BOARD",
        "E": "NHS NORTH EAST LONDON INTEGRATED CARE BOARD",
        "EC": "NHS NORTH EAST LONDON INTEGRATED CARE BOARD",
        "IG": "NHS NORTH EAST LONDON INTEGRATED CARE BOARD",
        "RM": "NHS NORTH EAST LONDON INTEGRATED CARE BOARD",
        "N": "NHS NORTH CENTRAL LONDON INTEGRATED CARE BOARD",
        "WC": "NHS NORTH CENTRAL LONDON INTEGRATED CARE BOARD",
        "SE": "NHS SOUTH EAST LONDON INTEGRATED CARE BOARD",
        "BR": "NHS SOUTH EAST LONDON INTEGRATED CARE BOARD",
        "DA": "NHS SOUTH EAST LONDON INTEGRATED CARE BOARD",
        "SW": "NHS SOUTH WEST LONDON INTEGRATED CARE BOARD",
        "SM": "NHS SOUTH WEST LONDON INTEGRATED CARE BOARD",
        "CR": "NHS SOUTH WEST LONDON INTEGRATED CARE BOARD",
        "TW": "NHS SOUTH WEST LONDON INTEGRATED CARE BOARD",
        "BN": "NHS SUSSEX INTEGRATED CARE BOARD",
        "RH": "NHS SUSSEX INTEGRATED CARE BOARD",
        "TN": "NHS SUSSEX INTEGRATED CARE BOARD",
        "LS": "NHS WEST YORKSHIRE INTEGRATED CARE BOARD",
        "BD": "NHS WEST YORKSHIRE INTEGRATED CARE BOARD",
        "WF": "NHS WEST YORKSHIRE INTEGRATED CARE BOARD",
        "HX": "NHS WEST YORKSHIRE INTEGRATED CARE BOARD",
        "HD": "NHS WEST YORKSHIRE INTEGRATED CARE BOARD",
        "PR": "NHS LANCASHIRE AND SOUTH CUMBRIA INTEGRATED CARE BOARD",
        "FY": "NHS LANCASHIRE AND SOUTH CUMBRIA INTEGRATED CARE BOARD",
        "LA": "NHS LANCASHIRE AND SOUTH CUMBRIA INTEGRATED CARE BOARD",
        "BB": "NHS LANCASHIRE AND SOUTH CUMBRIA INTEGRATED CARE BOARD",
        "ME": "NHS KENT AND MEDWAY INTEGRATED CARE BOARD",
        "CT": "NHS KENT AND MEDWAY INTEGRATED CARE BOARD",
        "YO": "NHS HUMBER AND NORTH YORKSHIRE INTEGRATED CARE BOARD",
        "HU": "NHS HUMBER AND NORTH YORKSHIRE INTEGRATED CARE BOARD",
        "SS": "NHS MID AND SOUTH ESSEX INTEGRATED CARE BOARD",
        "CM": "NHS MID AND SOUTH ESSEX INTEGRATED CARE BOARD",
        "CO": "NHS SUFFOLK AND NORTH EAST ESSEX INTEGRATED CARE BOARD",
        "AL": "NHS HERTFORDSHIRE AND WEST ESSEX INTEGRATED CARE BOARD",
        "SG": "NHS HERTFORDSHIRE AND WEST ESSEX INTEGRATED CARE BOARD",
        "WD": "NHS HERTFORDSHIRE AND WEST ESSEX INTEGRATED CARE BOARD",
        "EN": "NHS HERTFORDSHIRE AND WEST ESSEX INTEGRATED CARE BOARD",
        "RG": "NHS BUCKINGHAMSHIRE, OXFORDSHIRE AND BERKSHIRE WEST INTEGRATED CARE BOARD",
        "OX": "NHS BUCKINGHAMSHIRE, OXFORDSHIRE AND BERKSHIRE WEST INTEGRATED CARE BOARD",
        "HP": "NHS BUCKINGHAMSHIRE, OXFORDSHIRE AND BERKSHIRE WEST INTEGRATED CARE BOARD",
        "SL": "NHS FRIMLEY INTEGRATED CARE BOARD",
        "GU": "NHS SURREY HEARTLANDS INTEGRATED CARE BOARD",
        "KT": "NHS SURREY HEARTLANDS INTEGRATED CARE BOARD",
        "SO": "NHS HAMPSHIRE AND ISLE OF WIGHT INTEGRATED CARE BOARD",
        "PO": "NHS HAMPSHIRE AND ISLE OF WIGHT INTEGRATED CARE BOARD",
        "B": "NHS BIRMINGHAM AND SOLIHULL INTEGRATED CARE BOARD",
        "DY": "NHS BLACK COUNTRY INTEGRATED CARE BOARD",
        "WS": "NHS BLACK COUNTRY INTEGRATED CARE BOARD",
        "WV": "NHS BLACK COUNTRY INTEGRATED CARE BOARD",
        "CV": "NHS COVENTRY AND WARWICKSHIRE INTEGRATED CARE BOARD",
        "ST": "NHS STAFFORDSHIRE AND STOKE-ON-TRENT INTEGRATED CARE BOARD",
        "WR": "NHS HEREFORDSHIRE AND WORCESTERSHIRE INTEGRATED CARE BOARD",
        "HR": "NHS HEREFORDSHIRE AND WORCESTERSHIRE INTEGRATED CARE BOARD",
        "SY": "NHS SHROPSHIRE, TELFORD AND WREKIN INTEGRATED CARE BOARD",
        "TF": "NHS SHROPSHIRE, TELFORD AND WREKIN INTEGRATED CARE BOARD",
        "LE": "NHS LEICESTER, LEICESTERSHIRE AND RUTLAND INTEGRATED CARE BOARD",
        "NG": "NHS NOTTINGHAM AND NOTTINGHAMSHIRE INTEGRATED CARE BOARD",
        "DE": "NHS DERBY AND DERBYSHIRE INTEGRATED CARE BOARD",
        "LN": "NHS LINCOLNSHIRE INTEGRATED CARE BOARD",
        "NN": "NHS NORTHAMPTONSHIRE INTEGRATED CARE BOARD",
        "MK": "NHS BEDFORDSHIRE, LUTON AND MILTON KEYNES INTEGRATED CARE BOARD",
        "LU": "NHS BEDFORDSHIRE, LUTON AND MILTON KEYNES INTEGRATED CARE BOARD",
        "CB": "NHS CAMBRIDGESHIRE AND PETERBOROUGH INTEGRATED CARE BOARD",
        "PE": "NHS CAMBRIDGESHIRE AND PETERBOROUGH INTEGRATED CARE BOARD",
        "IP": "NHS NORFOLK AND WAVENEY INTEGRATED CARE BOARD",
        "NR": "NHS NORFOLK AND WAVENEY INTEGRATED CARE BOARD",
        "BS": "NHS BRISTOL, NORTH SOMERSET AND SOUTH GLOUCESTERSHIRE INTEGRATED CARE BOARD",
        "GL": "NHS GLOUCESTERSHIRE INTEGRATED CARE BOARD",
        "BA": "NHS BATH AND NORTH EAST SOMERSET, SWINDON AND WILTSHIRE INTEGRATED CARE BOARD",
        "SN": "NHS BATH AND NORTH EAST SOMERSET, SWINDON AND WILTSHIRE INTEGRATED CARE BOARD",
        "SP": "NHS BATH AND NORTH EAST SOMERSET, SWINDON AND WILTSHIRE INTEGRATED CARE BOARD",
        "TA": "NHS SOMERSET INTEGRATED CARE BOARD",
        "EX": "NHS DEVON INTEGRATED CARE BOARD",
        "TQ": "NHS DEVON INTEGRATED CARE BOARD",
        "PL": "NHS DEVON INTEGRATED CARE BOARD",
        "TR": "NHS CORNWALL AND THE ISLES OF SCILLY INTEGRATED CARE BOARD",
        "BH": "NHS DORSET INTEGRATED CARE BOARD",
        "DT": "NHS DORSET INTEGRATED CARE BOARD",
        "S": "NHS SOUTH YORKSHIRE INTEGRATED CARE BOARD",
        "DN": "NHS SOUTH YORKSHIRE INTEGRATED CARE BOARD",
    }

    DEMO_MH_WAITS = {
        "NHS GREATER MANCHESTER INTEGRATED CARE BOARD": 34,
        "NHS NORTH EAST AND NORTH CUMBRIA INTEGRATED CARE BOARD": 29,
        "NHS CHESHIRE AND MERSEYSIDE INTEGRATED CARE BOARD": 31,
        "NHS NORTH WEST LONDON INTEGRATED CARE BOARD": 26,
        "NHS NORTH EAST LONDON INTEGRATED CARE BOARD": 33,
        "NHS SUSSEX INTEGRATED CARE BOARD": 22,
        "NHS WEST YORKSHIRE INTEGRATED CARE BOARD": 52,
        "NHS LANCASHIRE AND SOUTH CUMBRIA INTEGRATED CARE BOARD": 19,
        "NHS BUCKINGHAMSHIRE, OXFORDSHIRE AND BERKSHIRE WEST INTEGRATED CARE BOARD": 18,
        "NHS BIRMINGHAM AND SOLIHULL INTEGRATED CARE BOARD": 36,
        "NHS BRISTOL, NORTH SOMERSET AND SOUTH GLOUCESTERSHIRE INTEGRATED CARE BOARD": 24,
        "NHS DEVON INTEGRATED CARE BOARD": 30,
        "NHS SOUTH YORKSHIRE INTEGRATED CARE BOARD": 27,
    }

    PROGRAMME_DIRECTORY = {
        "anxiety_panic": {
            "name": "Anxiety, Panic & Acute Overwhelm",
            "tagline": "Calm your nervous system, dismantle panic cycles, and connect with people who understand.",
            "podcasts": [
                {
                    "title": "The Anxious Truth (Episode: Demystifying Panic Attacks)",
                    "host": "Drew Linsalata",
                    "desc": "A no-fluff guide to understanding how panic attacks trigger in the body, why they cannot kill or hurt you, and how to stop fighting the adrenaline surge.",
                    "url": "https://theanxioustruth.com",
                    "duration": "24 mins",
                    "why_listen": "Teaches the exact physiological reason your chest feels tight and how surrendering to sensations halts the panic loop."
                },
                {
                    "title": "Huberman Lab: Master Your Nervous System & Reduce Stress",
                    "host": "Dr. Andrew Huberman (Stanford Neurobiologist)",
                    "desc": "The clinical science of the 'Physiological Sigh' (double inhale, long exhale) and fast tools to down-regulate high autonomic arousal.",
                    "url": "https://www.hubermanlab.com",
                    "duration": "35 mins",
                    "why_listen": "Fastest scientifically validated somatic intervention to lower heart rate within 30 seconds."
                },
                {
                    "title": "Owning It: The Anxiety Podcast",
                    "host": "Caroline Foran",
                    "desc": "Empathetic, vulnerable interviews and practical tools to untangle anticipatory anxiety and morning dread.",
                    "url": "https://play.acast.com/s/owning-it-the-anxiety-podcast",
                    "duration": "28 mins",
                    "why_listen": "Normalizes anxiety as a human nervous system reflex rather than a personal flaw."
                }
            ],
            "animated_videos": [
                {
                    "title": "How a Panic Attack Happens & How to Break the Cycle",
                    "creator": "TED-Ed Animation",
                    "desc": "Visually illustrates the amygdala alarm system, adrenaline flooding the bloodstream, and why panic reaches a biological peak within 10 minutes.",
                    "url": "https://www.ted.com/talks",
                    "key_takeaway": "Adrenaline has a finite biological half-life. If you do not add catastrophe thoughts, panic physically subsides in minutes."
                },
                {
                    "title": "The Fight-Flight-Freeze Response Explained",
                    "creator": "Psych Hub",
                    "desc": "An animated breakdown of physical sensations: dizziness, hyperventilation, and tingling numbness.",
                    "url": "https://psychhub.com",
                    "key_takeaway": "Your body is preparing to protect you, not harm you. Understanding sensations removes the fear of the fear."
                }
            ],
            "peer_communities": [
                {
                    "name": "No Panic UK Peer Support Groups",
                    "platform": "Weekly Telephone & Zoom Groups (UK-wide)",
                    "desc": "Mutual aid circles facilitated by trained volunteers who have recovered from panic disorder, phobias, and OCD.",
                    "url": "https://nopanic.org.uk",
                    "how_they_help": "Speak directly to peers who know the exact physical sensations of panic — no judgment, zero pressure to speak."
                },
                {
                    "name": "Mind: Side by Side Online Peer Community",
                    "platform": "24/7 Moderated Safe Online Community",
                    "desc": "A supportive online space run by Mind where thousands of UK residents share daily coping tips and encourage each other.",
                    "url": "https://sidebyside.mind.org.uk",
                    "how_they_help": "Post anytime day or night when feeling overwhelmed; receive supportive replies from fellow members."
                }
            ],
            "activities": [
                {
                    "title": "Mammalian Dive Reflex Reset (Somatic)",
                    "type": "Nervous System Calming",
                    "duration": "2 mins",
                    "desc": "Submerge your hands in ice water or hold an ice pack gently against your cheekbones and upper eyelids for 30 seconds. This triggers the vagus nerve and drops heart rate immediately."
                },
                {
                    "title": "5-4-3-2-1 Sensory Nature Walk (Social Prescribing)",
                    "type": "Outdoor Grounding",
                    "duration": "15 mins",
                    "desc": "Walk outdoors without headphones. Specifically notice 5 green objects, 4 physical textures, 3 distinct sounds, 2 scents, and 1 taste."
                }
            ],
            "seven_day_plan": [
                {"day": "Day 1", "title": "Somatic Safety Reset", "micro_step": "Practice the physiological sigh 5 times in the morning. Bookmark the No Panic peer hotline."},
                {"day": "Day 2", "title": "Knowledge is Power", "micro_step": "Watch the 5-minute animated video on why panic cannot harm your heart."},
                {"day": "Day 3", "title": "Break the Isolation", "micro_step": "Join Mind's Side by Side online community and read 3 peer threads."},
                {"day": "Day 4", "title": "Sensory Exposure Walk", "micro_step": "Take a 15-minute gentle outdoor sensory walk without your phone."},
                {"day": "Day 5", "title": "Audio Companion", "micro_step": "Listen to Episode 1 of The Anxious Truth on how to stop fighting physical symptoms."},
                {"day": "Day 6", "title": "Boundary & Rest Slot", "micro_step": "Set a dedicated 15-minute 'worry window' at 5:00 PM; postpone morning worries until then."},
                {"day": "Day 7", "title": "Weekly Reflection", "micro_step": "Note down 2 moments this week where panic peaked and then subsided on its own."}
            ]
        },

        "depression_low_mood": {
            "name": "Depression, Low Mood & Lethargy",
            "tagline": "Rebuild momentum with compassionate micro-actions, neurobiology animations, and peer walking circles.",
            "podcasts": [
                {
                    "title": "Feel Better Live More: The Depression Toolkit",
                    "host": "Dr. Rangan Chatterjee",
                    "desc": "How morning sunlight, micro-movements, and low-friction social connection rebuild neurotransmitter balance.",
                    "url": "https://drchatterjee.com/blog/category/podcast/",
                    "duration": "45 mins",
                    "why_listen": "Provides realistic, zero-pressure steps you can do even when getting out of bed feels impossible."
                },
                {
                    "title": "The Hilarious World of Depression",
                    "host": "John Moe",
                    "desc": "Comedians, writers, and public figures openly discussing clinical depression with humor, honesty, and warmth.",
                    "url": "https://www.hilariousworld.org",
                    "duration": "35 mins",
                    "why_listen": "Removes the heavy shame and isolation of depression; makes you laugh when you least expect it."
                }
            ],
            "animated_videos": [
                {
                    "title": "I Had a Black Dog, His Name Was Depression",
                    "creator": "World Health Organization (WHO Official)",
                    "desc": "The acclaimed animated story illustrating what clinical depression feels like and the journey to taming the beast.",
                    "url": "https://www.youtube.com/watch?v=XiCrni9ND44",
                    "key_takeaway": "Depression is an illness of depletion, not a weakness of character. Small daily actions gradually tame the black dog."
                }
            ],
            "peer_communities": [
                {
                    "name": "Andy's Man Club (For Men)",
                    "platform": "180+ In-Person Weekly Clubs across England (Every Monday 7 PM)",
                    "desc": "Free, non-judgmental talking groups for men to open up about life challenges and depression over a brew and a biscuit.",
                    "url": "https://andysmanclub.co.uk",
                    "how_they_help": "No referral needed, zero pressure to speak, completely free. Has saved thousands of men's lives."
                },
                {
                    "name": "Mental Health Mates (Walk & Talk)",
                    "platform": "Free Community Walking Groups across the UK",
                    "desc": "Safe walking groups where people with depression and mental illness walk together in parks.",
                    "url": "https://www.mentalhealthmates.co.uk",
                    "how_they_help": "Walking side-by-side takes the awkwardness out of eye contact; gentle, outdoors, friendly."
                }
            ],
            "activities": [
                {
                    "title": "10-Minute Morning Daylight Ritual (Neurochemical)",
                    "type": "Circadian Biology",
                    "duration": "10 mins",
                    "desc": "Step outside within 60 minutes of waking. Viewing natural photons triggers cortisol release and sets your dopamine rhythm."
                },
                {
                    "title": "The 'One Micro-Task' Rule",
                    "type": "Behavioural Activation",
                    "duration": "3 mins",
                    "desc": "Pick one tiny task (open the blinds, wash one mug, or drink one glass of water). Complete it and give yourself full credit."
                }
            ],
            "seven_day_plan": [
                {"day": "Day 1", "title": "Circadian Daylight", "micro_step": "Step outside for 10 minutes in the morning, even on an overcast day."},
                {"day": "Day 2", "title": "Kind Self-Talk", "micro_step": "Watch the WHO 'Black Dog of Depression' animation to release self-blame."},
                {"day": "Day 3", "title": "Micro-Momentum", "micro_step": "Complete one 3-minute micro-task (make the bed or wash one cup)."},
                {"day": "Day 4", "title": "Human Warmth", "micro_step": "Send one simple emoji or check-in text to someone you care about."},
                {"day": "Day 5", "title": "Podcast Company", "micro_step": "Listen to an episode of The Hilarious World of Depression while wrapped in a blanket."},
                {"day": "Day 6", "title": "Community Connection", "micro_step": "Find a local Mental Health Mates or Andy's Man Club meeting for the week ahead."},
                {"day": "Day 7", "title": "Celebrate Survival", "micro_step": "Acknowledge that surviving a tough week with depression is hard work, and you made it through."}
            ]
        },

        "work_burnout_stress": {
            "name": "Workplace Burnout & Chronic Stress",
            "tagline": "Protect your career, establish nervous-system boundaries, and claim free government workplace support.",
            "podcasts": [
                {
                    "title": "WorkLife with Adam Grant",
                    "host": "Adam Grant (Organizational Psychologist)",
                    "desc": "Evidence-based strategies on tackling toxic workloads, dealing with exhausting bosses, and finding psychological safety.",
                    "url": "https://adamgrant.net/podcasts/worklife/",
                    "duration": "35 mins",
                    "why_listen": "Helps distinguish between personal exhaustion and organizational dysfunction."
                },
                {
                    "title": "Eat Sleep Work Repeat",
                    "host": "Bruce Daisley (Ex-Twitter VP)",
                    "desc": "Conversations with neurologists and workplace experts on why burnout is an occupational phenomenon and how to heal.",
                    "url": "https://eatsleepworkrepeat.com",
                    "duration": "30 mins",
                    "why_listen": "Provides realistic workplace survival tactics."
                }
            ],
            "animated_videos": [
                {
                    "title": "The 3 Stages of Burnout Explained",
                    "creator": "Sprouts Cognitive Science Animations",
                    "desc": "How chronic cortisol exposure causes emotional exhaustion, depersonalization/cynicism, and reduced personal efficacy.",
                    "url": "https://sproutsschools.com",
                    "key_takeaway": "Burnout is not resolved by a weekend off; it requires pacing and nervous system boundary restructuring."
                }
            ],
            "peer_communities": [
                {
                    "name": "Able Futures & Maximus Peer Support Network",
                    "platform": "Free Government Access to Work Coaching (UK-wide)",
                    "desc": "Free 1-to-1 mental health coaching funded by the Department for Work and Pensions (DWP) to help you keep your job.",
                    "url": "https://able-futures.co.uk",
                    "how_they_help": "9 months of confidential mental health support; zero charge to you or your company."
                }
            ],
            "activities": [
                {
                    "title": "The 8 PM Digital Sunset Ritual",
                    "type": "Boundary Setting",
                    "duration": "Evening",
                    "desc": "Shut down work laptops, mute Slack/Teams notifications, and place your phone in another room by 8:00 PM."
                },
                {
                    "title": "Cognitive Brain-Dump Paper Journal",
                    "type": "Cognitive Offloading",
                    "duration": "7 mins",
                    "desc": "Before bed, write down every unfinished work task or worry on a blank sheet of paper. Closes open mental loops."
                }
            ],
            "seven_day_plan": [
                {"day": "Day 1", "title": "Energy Audit", "micro_step": "List the top 3 work tasks that drain you the most."},
                {"day": "Day 2", "title": "Digital Sunset", "micro_step": "Turn off work notifications at 6:00 PM sharp."},
                {"day": "Day 3", "title": "Access to Work Grant", "micro_step": "Submit a free 5-minute online application for DWP Access to Work coaching."},
                {"day": "Day 4", "title": "Screen-Free Lunch", "micro_step": "Eat lunch away from your desk and take a 10-minute walk."},
                {"day": "Day 5", "title": "Set One Boundary", "micro_step": "Decline or reschedule one non-essential meeting with a polite standard template."},
                {"day": "Day 6", "title": "Complete Brain Dump", "micro_step": "Write all weekend worries down on paper, close the notebook, and leave it on your desk."},
                {"day": "Day 7", "title": "Full Work Disconnect", "micro_step": "Spend Sunday entirely work-free without checking work email."}
            ]
        },

        "grief_bereavement": {
            "name": "Grief, Loss & Bereavement",
            "tagline": "Gentle companionship, poignant lived-experience audio, and mutual bereavement circles.",
            "podcasts": [
                {
                    "title": "Griefcast",
                    "host": "Cariad Lloyd (Award-winning UK Comedian & Author)",
                    "desc": "Funny, human, and deeply moving conversations about death, loss, and how we carry on after people die.",
                    "url": "https://cariadlloyd.com/griefcast",
                    "duration": "45 mins",
                    "why_listen": "Proves that you can laugh, cry, and be completely messy with grief; feels like sitting with a warm friend."
                }
            ],
            "animated_videos": [
                {
                    "title": "The Ball in the Box Theory of Grief",
                    "creator": "Visual Grief Education",
                    "desc": "Explains why grief feels massive at first, and why it still hits painfully later even as life grows around it.",
                    "url": "https://www.cruse.org.uk",
                    "key_takeaway": "Grief never shrinks; your life grows around it."
                }
            ],
            "peer_communities": [
                {
                    "name": "Cruse Bereavement Peer Groups",
                    "platform": "Local Groups & Helpline Across England",
                    "desc": "The UK's largest bereavement charity connecting people navigating partner, parent, child, or friend loss.",
                    "url": "https://www.cruse.org.uk",
                    "how_they_help": "Safe, confidential peer circles led by experienced bereavement volunteers."
                }
            ],
            "activities": [
                {
                    "title": "Memory Journaling / Letters to the Unseen",
                    "type": "Expressive Writing",
                    "duration": "15 mins",
                    "desc": "Write a letter expressing whatever thoughts, memories, or frustrations you wish you could share."
                }
            ],
            "seven_day_plan": [
                {"day": "Day 1", "title": "Permission to Feel", "micro_step": "Acknowledge today without judging your grief level."},
                {"day": "Day 2", "title": "The Ball in the Box", "micro_step": "Watch the 4-minute animated video on the ball in the box theory of grief."},
                {"day": "Day 3", "title": "Warm Audio", "micro_step": "Listen to one episode of Griefcast while making a cup of tea."},
                {"day": "Day 4", "title": "Physical Nourishment", "micro_step": "Drink extra water and eat a warm, nourishing meal."},
                {"day": "Day 5", "title": "Peer Connection", "micro_step": "Check out Cruse peer support forums online."},
                {"day": "Day 6", "title": "Memory Slot", "micro_step": "Light a candle or write down one favorite memory of your loved one."},
                {"day": "Day 7", "title": "Gentle Pacing", "micro_step": "Take a quiet 15-minute nature walk; give yourself grace for the week ahead."}
            ]
        },

        "youth_student": {
            "name": "Young Adults & Student Mental Health",
            "tagline": "Exam anxiety, social comparison, student life, and anonymous youth peer communities.",
            "podcasts": [
                {
                    "title": "Life Hacks by BBC Radio 1",
                    "host": "BBC Radio 1",
                    "desc": "Frank, practical conversations on surviving university, peer pressure, loneliness, and mental health.",
                    "url": "https://www.bbc.co.uk/programmes/b09b1145",
                    "duration": "30 mins",
                    "why_listen": "Directly addresses youth-specific struggles without talking down to you."
                }
            ],
            "animated_videos": [
                {
                    "title": "Exam Stress and the Adolescent Brain",
                    "creator": "BBC Bitesize Animations",
                    "desc": "How adrenaline affects short-term memory during exams and how to pace study sessions calmly.",
                    "url": "https://www.bbc.co.uk/bitesize",
                    "key_takeaway": "Short 25-minute study intervals with physical movement beats 4-hour cramming panic."
                }
            ],
            "peer_communities": [
                {
                    "name": "The Mix Discussion Boards (Under 25s)",
                    "platform": "24/7 Moderated Online Youth Boards",
                    "desc": "The UK's leading support service for young people under 25 on relationships, mental health, money, and uni.",
                    "url": "https://www.themix.org.uk",
                    "how_they_help": "Completely anonymous peer forums moderated by safeguarding professionals."
                }
            ],
            "activities": [
                {
                    "title": "Pomodoro 25/5 Study Flow",
                    "type": "Academic Pacing",
                    "duration": "30 mins",
                    "desc": "Study for 25 minutes, then get up and stretch for 5 minutes. Breaks exam panic loops."
                }
            ],
            "seven_day_plan": [
                {"day": "Day 1", "title": "Check In", "micro_step": "Acknowledge what is stressing you out most at school/uni."},
                {"day": "Day 2", "title": "The Mix Community", "micro_step": "Explore The Mix peer discussion boards anonymously."},
                {"day": "Day 3", "title": "Podcast Listen", "micro_step": "Listen to one episode of BBC Radio 1 Life Hacks on student stress."},
                {"day": "Day 4", "title": "Screen Boundary", "micro_step": "Place phone across the room when studying for 45 minutes."},
                {"day": "Day 5", "title": "Kooth Exploration", "micro_step": "Register an anonymous profile on Kooth.com if you want to chat to someone."},
                {"day": "Day 6", "title": "Movement Break", "micro_step": "Do a 20-minute cycle or brisk walk with a friend."},
                {"day": "Day 7", "title": "Study Reset", "micro_step": "Organize your study desk and write down 3 clear priorities for next week."}
            ]
        },

        "ocd_intrusive_thoughts": {
            "name": "OCD, Intrusive Thoughts & Health Anxiety",
            "tagline": "ERP tools, demystifying bizarre intrusive thoughts, and specialized mutual aid groups.",
            "podcasts": [
                {
                    "title": "The OCD Stories",
                    "host": "Stuart Ralph",
                    "desc": "In-depth recovery stories and interviews with leading Exposure and Response Prevention (ERP) specialists.",
                    "url": "https://theocdstories.com",
                    "duration": "45 mins",
                    "why_listen": "Normalizes disturbing intrusive thoughts and shows full recovery is possible."
                }
            ],
            "animated_videos": [
                {
                    "title": "The OCD Cycle: Obsession, Anxiety, Compulsion, Relief",
                    "creator": "International OCD Foundation Animations",
                    "desc": "How performing mental or physical rituals reinforces the brain's false alarm system.",
                    "url": "https://iocdf.org",
                    "key_takeaway": "Compulsions provide short-term relief at the cost of long-term suffering. Resisting compulsions resets the amygdala."
                }
            ],
            "peer_communities": [
                {
                    "name": "OCD Action Peer Support Groups",
                    "platform": "Weekly Zoom Circles & Youth Groups across UK",
                    "desc": "The UK's largest OCD charity running weekly peer groups for adults, parents, and young people.",
                    "url": "https://ocdaction.org.uk",
                    "how_they_help": "Talk openly about intrusive thoughts without fear of shock or misunderstanding."
                }
            ],
            "activities": [
                {
                    "title": "The 5-Minute Compulsion Postponement Game",
                    "type": "ERP Technique",
                    "duration": "5 mins",
                    "desc": "When the urge to check or google arises, set a timer for 5 minutes. Sit with uncertainty before deciding."
                }
            ],
            "seven_day_plan": [
                {"day": "Day 1", "title": "Dismantle Stigma", "micro_step": "Acknowledge that having an intrusive thought does not mean you want to do it."},
                {"day": "Day 2", "title": "Watch the OCD Cycle", "micro_step": "Watch the animated video on how compulsions fuel the OCD monster."},
                {"day": "Day 3", "title": "Postpone One Check", "micro_step": "Delay one reassurance question or google search by 5 minutes."},
                {"day": "Day 4", "title": "Listen to a Recovery Story", "micro_step": "Listen to 1 episode of The OCD Stories podcast."},
                {"day": "Day 5", "title": "Peer Solidarity", "micro_step": "Visit ocdaction.org.uk and view their peer group timetable."},
                {"day": "Day 6", "title": "Label the Intrusion", "micro_step": "When a scary thought arrives, say: 'This is an OCD thought, not a fact.'"},
                {"day": "Day 7", "title": "Celebrate Courage", "micro_step": "Congratulate yourself for tolerating uncertainty this week."}
            ]
        }
    }

    def __init__(self):
        self.organisations = self._load_organisations()
        self.rtt_data = self._load_rtt_data()

    def _load_organisations(self) -> List[Dict[str, Any]]:
        path = _find("organisations.csv")
        orgs = []
        if os.path.exists(path):
            with open(path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    orgs.append(row)
        return orgs

    def _load_rtt_data(self) -> Dict[str, Dict[str, Any]]:
        path = _find("rtt_by_icb_real.csv")
        data = {}
        if os.path.exists(path):
            with open(path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    icb = row["icb_region"].strip()
                    try:
                        pts = int(row["patients_waiting"])
                    except (ValueError, KeyError):
                        pts = 0
                    try:
                        wait = float(row["physical_health_wait_weeks"])
                    except (ValueError, KeyError):
                        wait = 15.6
                    data[icb] = {
                        "patients_waiting": pts,
                        "physical_wait_weeks": wait,
                        "mh_wait_weeks": self.DEMO_MH_WAITS.get(icb, 28)
                    }
        return data

    def detect_crisis(self, text: str) -> Dict[str, Any]:
        lower = text.lower()
        matched = [k for k in self.CRISIS_KEYWORDS if k in lower]
        if matched:
            return {
                "is_crisis": True,
                "keywords": matched,
                "urgent_message": (
                    "🚨 **IMMEDIATE HUMAN SUPPORT AVAILABLE RIGHT NOW (FREE & 24/7)**\n\n"
                    "If you are feeling overwhelmed or having thoughts of hurting yourself, please pause here. "
                    "You do not have to carry this alone:\n\n"
                    "- 📞 **Samaritans**: Call **116 123** (Free from any phone, 24/7 confidential listening)\n"
                    "- 📱 **Shout Crisis Text Line**: Text **SHOUT** to **85258** (Free, confidential 24/7 text support)\n"
                    "- 🏥 **NHS Urgent Mental Health Team**: Call **111 and select option 2** (Direct access to NHS triage)\n"
                    "- 🚑 If you are in immediate physical danger, call **999** or go to your nearest **A&E**."
                )
            }
        return {"is_crisis": False, "keywords": [], "urgent_message": ""}

    def resolve_postcode(self, postcode_raw: str) -> Dict[str, Any]:
        cleaned = re.sub(r"[^A-Za-z0-9]", "", postcode_raw.strip().upper())
        match = re.match(r"^([A-Z]{1,2})", cleaned)
        prefix = match.group(1) if match else ""
        
        icb_name = self.POSTCODE_TO_ICB.get(prefix, "NHS BUCKINGHAMSHIRE, OXFORDSHIRE AND BERKSHIRE WEST INTEGRATED CARE BOARD")
        is_exact = prefix in self.POSTCODE_TO_ICB

        icb_info = self.rtt_data.get(icb_name, {
            "patients_waiting": 182649,
            "physical_wait_weeks": 15.0,
            "mh_wait_weeks": 28
        })

        return {
            "postcode": postcode_raw.upper(),
            "prefix": prefix,
            "is_matched": is_exact,
            "icb_name": icb_name,
            "patients_waiting": icb_info["patients_waiting"],
            "physical_wait_weeks": icb_info["physical_wait_weeks"],
            "mh_wait_weeks": icb_info["mh_wait_weeks"],
            "wait_gap_weeks": round(icb_info["mh_wait_weeks"] - icb_info["physical_wait_weeks"], 1),
            "ratio": round(icb_info["mh_wait_weeks"] / max(icb_info["physical_wait_weeks"], 1), 1)
        }

    def get_available_programmes(self) -> Dict[str, str]:
        return {k: v["name"] for k, v in self.PROGRAMME_DIRECTORY.items()}

    def get_personalized_programme(self, problem_key: str) -> Dict[str, Any]:
        return self.PROGRAMME_DIRECTORY.get(problem_key, self.PROGRAMME_DIRECTORY["anxiety_panic"])

    def match_programme_from_narrative(self, story: str) -> str:
        story_lower = story.lower()
        if any(w in story_lower for w in ["work", "burnout", "boss", "job", "career", "desk", "colleague"]):
            return "work_burnout_stress"
        if any(w in story_lower for w in ["grief", "bereave", "death", "lost my", "funeral", "passed away"]):
            return "grief_bereavement"
        if any(w in story_lower for w in ["teen", "student", "exam", "uni", "school", "under 18", "college"]):
            return "youth_student"
        if any(w in story_lower for w in ["ocd", "intrusive", "compuls", "check", "ritual"]):
            return "ocd_intrusive_thoughts"
        if any(w in story_lower for w in ["depress", "low mood", "sad", "empty", "hopeless", "numb"]):
            return "depression_low_mood"
        return "anxiety_panic"

    def score_phq9(self, answers: List[int]) -> Dict[str, Any]:
        score = sum(answers[:9])
        q9_self_harm = answers[8] if len(answers) >= 9 else 0
        if score <= 4:
            severity = "None-minimal depression"
            action = "Supportive monitoring, self-care, and lifestyle advice."
        elif score <= 9:
            severity = "Mild depression"
            action = "Watchful waiting; guided self-help, low-intensity CBT."
        elif score <= 14:
            severity = "Moderate depression"
            action = "Clinical referral recommended (NHS Talking Therapies, Step 2/3 CBT, counselling)."
        elif score <= 19:
            severity = "Moderately severe depression"
            action = "Active clinical intervention, GP consultation, combined psychological therapy."
        else:
            severity = "Severe depression"
            action = "Urgent clinical evaluation by GP and mental health specialist team."

        return {
            "score": score,
            "max_score": 27,
            "severity": severity,
            "action": action,
            "self_harm_risk": q9_self_harm > 0
        }

    def score_gad7(self, answers: List[int]) -> Dict[str, Any]:
        score = sum(answers[:7])
        if score <= 4:
            severity = "Minimal anxiety"
            action = "Reassurance, lifestyle interventions, and grounding."
        elif score <= 9:
            severity = "Mild anxiety"
            action = "Low-intensity cognitive behavioral intervention and guided digital tools."
        elif score <= 14:
            severity = "Moderate anxiety"
            action = "Formal referral for high-intensity CBT or talking therapy."
        else:
            severity = "Severe anxiety"
            action = "Specialist clinical review; comprehensive assessment and GP intervention."

        return {
            "score": score,
            "max_score": 21,
            "severity": severity,
            "action": action,
        }

    def get_right_to_choose_providers(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Psychiatry-UK",
                "specialisms": "Adult ADHD, Adult Autism, Clinical Psychiatry",
                "typical_wait": "12 to 18 weeks (vs NHS 2-3 years)",
                "modality": "100% Online / Video Consultations (UK-wide)",
                "cost": "Free under NHS Right to Choose",
                "how_to_access": "Download GP referral letter from psychiatry-uk.com and ask GP to submit via e-Referral.",
                "url": "https://psychiatry-uk.com/right-to-choose/"
            },
            {
                "name": "ProblemShared",
                "specialisms": "ADHD & Autism Assessments, Psychological Therapies",
                "typical_wait": "12 to 16 weeks",
                "modality": "Online Video (England-wide NHS contracts)",
                "cost": "Free under NHS Right to Choose",
                "how_to_access": "Request your GP send standard referral to referrals@problemshared.net with their NHS referral form.",
                "url": "https://www.problemshared.net/right-to-choose"
            },
            {
                "name": "ADHD 360",
                "specialisms": "Adult & Child Neurodevelopmental Assessments (ADHD)",
                "typical_wait": "14 to 20 weeks",
                "modality": "Online & App-supported titration",
                "cost": "Free under NHS Right to Choose",
                "how_to_access": "Complete the ADHD 360 intake pack and ask GP to refer via their dedicated NHS portal.",
                "url": "https://www.adhd-360.com/right-to-choose/"
            },
            {
                "name": "Clinical Partners",
                "specialisms": "Adult & Child ASD/ADHD Diagnostics & Mental Health Assessments",
                "typical_wait": "14 to 22 weeks",
                "modality": "Online & In-person clinics in select cities",
                "cost": "Free under NHS Right to Choose",
                "how_to_access": "GP submits referral directly citing patient's legal right to choose under NHS Constitution.",
                "url": "https://www.clinical-partners.co.uk/nhs-services/right-to-choose"
            },
            {
                "name": "Vita Health Group",
                "specialisms": "NHS Talking Therapies (Anxiety, Depression, Trauma, Bereavement)",
                "typical_wait": "3 to 6 weeks in commissioned ICBs",
                "modality": "Online, Phone, Video & In-person",
                "cost": "Free (NHS Commissioned)",
                "how_to_access": "Direct self-referral available in participating ICBs or via GP referral.",
                "url": "https://www.vitahealthgroup.co.uk/nhs-services/nhs-mental-health/"
            },
            {
                "name": "Insight Healthcare",
                "specialisms": "Psychological therapies, IAPT CBT, Counselling",
                "typical_wait": "4 to 8 weeks",
                "modality": "Online & In-person across Midlands and North",
                "cost": "Free (NHS Commissioned)",
                "how_to_access": "Self-refer online or ask GP to direct IAPT referral to Insight.",
                "url": "https://www.insighthealthcare.org/"
            }
        ]

    def get_workplace_and_dwp_guide(self) -> Dict[str, Any]:
        return {
            "access_to_work": {
                "title": "DWP Access to Work Mental Health Support",
                "summary": "A free UK government grant (up to £66,000/year) designed to help people with mental health conditions stay in work.",
                "benefits": [
                    "Up to 9 months of 1-to-1 work-mental health coping coaching from Maximus or Able Futures.",
                    "No cost to you or your employer; completely confidential from your boss.",
                    "Funding for workplace adjustments, noise-cancelling equipment, or tailored software.",
                    "Travel assistance funding if anxiety or panic prevents using public transport."
                ],
                "apply_link": "https://www.gov.uk/access-to-work"
            },
            "equality_act_rights": {
                "title": "Equality Act 2010 — Reasonable Adjustments at Work",
                "summary": "If your mental health condition has lasted (or is likely to last) 12 months and affects your daily life, it is legally defined as a disability under Section 6.",
                "protections": [
                    "Your employer has a legal duty to make Reasonable Adjustments (e.g. flexible start times, hybrid working, quiet desks).",
                    "You cannot be lawfully dismissed or disciplined solely for disability-related absences without reasonable adjustments being explored first.",
                    "You have the right to request a phased return to work after sick leave."
                ]
            },
            "fit_notes": {
                "title": "Smart Fit Notes ('May be fit for work')",
                "summary": "You don't have to be signed off 100% sick. Ask your GP for a fit note that checks 'May be fit for work with adjustments'.",
                "options": [
                    "Phased return to work (e.g. 3 days/week building up to 5).",
                    "Altered hours (avoiding rush-hour commute panic).",
                    "Amended duties (temporarily removing high-stress client calls).",
                    "Workplace adaptations (working from home 3-4 days/week)."
                ]
            }
        }

    def generate_mp_advocacy_letter(
        self, constituent_name: str, postcode: str, local_mp: str, weeks_waiting: int, condition: str
    ) -> str:
        loc = self.resolve_postcode(postcode)
        icb_name = loc["icb_name"]
        return f"""**URGENT CONSTITUENT CORRESPONDENCE: MENTAL HEALTH BACKLOG & ECONOMIC IMPACT**

**Date:** {date.today().strftime('%d %B %Y')}
**To:** {local_mp.strip() or 'My Member of Parliament'}
**House of Commons, London, SW1A 0AA**
**From:** {constituent_name.strip() or '[Constituent Name]'}
**Postcode:** {postcode.upper()} (Integrated Care Board: {icb_name})

---

**Dear {local_mp.strip() or 'Member of Parliament'},**

**RE: Extreme mental health waiting times and economic inactivity in {icb_name}**

I am writing to you as your constituent to raise urgent concern regarding the crisis in NHS mental health provision and its direct link to local economic inactivity.

I have currently been waiting **{weeks_waiting} weeks** for NHS mental health treatment for **{condition}**. In our local Integrated Care Board (**{icb_name}**), patients face median mental health waits of **{loc['mh_wait_weeks']} weeks** — compared to a physical health wait of **{loc['physical_wait_weeks']} weeks**.

### The Human & Economic Reality:
1. **The Postcode Lottery:** In neighbouring regions, patients receive treatment within weeks, whereas in our area, hundreds of people are left stranded for months without clinical support.
2. **Economic Inactivity:** Nationally, 2.8 million people are out of work due to long-term sickness, with mental ill-health being the primary driver, costing the UK economy an estimated £28 billion annually.
3. **Parity of Esteem:** The Health and Social Care Act legally enshrined 'parity of esteem' between physical and mental health. A 30+ week wait for psychological intervention directly breaches the spirit of that legislation.

### My Ask of You as My MP:
1. **Submit a Parliamentary Question** to the Secretary of State for Health and Social Care regarding the variance in mental health waiting times across {icb_name}.
2. **Request an urgent briefing** with the Chief Executive of {icb_name} on their plans to eliminate out-of-area waiting disparities and enforce the NHS Choice Framework.
3. **Advocate for expanded commissioning** of Any Qualified Providers (AQPs) so patients are not forced to suffer avoidable vocational and psychological decline.

Yours sincerely,

**{constituent_name.strip() or '[Constituent Name]'}**
*Sent via NHS Mental Health & Economic Inactivity Navigator (mh-navigator)*
"""

    def triage_narrative(self, user_story: str) -> Dict[str, Any]:
        crisis_check = self.detect_crisis(user_story)
        if crisis_check["is_crisis"]:
            immediate_orgs = [o for o in self.organisations if o.get("urgency_level") == "immediate"]
            return {
                "crisis": crisis_check,
                "detected_tags": ["crisis"],
                "urgency": "immediate",
                "summary": "Urgent emotional distress / crisis detected.",
                "matches": immediate_orgs[:3]
            }

        story_lower = user_story.lower()
        tags = set()

        if any(w in story_lower for w in ["anxi", "panic", "worry", "fear", "heart racing", "overthink"]):
            tags.add("anxiety")
        if any(w in story_lower for w in ["depress", "low mood", "sad", "empty", "hopeless", "numb", "exhaust"]):
            tags.add("depression")
        if any(w in story_lower for w in ["trauma", "ptsd", "flashback", "nightmare", "abuse", "assault"]):
            tags.add("trauma")
        if any(w in story_lower for w in ["ocd", "obsess", "compuls", "intrusive thought", "ritual"]):
            tags.add("ocd")
        if any(w in story_lower for w in ["grief", "bereave", "lost someone", "funeral", "death of"]):
            tags.add("grief")
        if any(w in story_lower for w in ["eat", "anorex", "bulim", "body image", "purging", "starv"]):
            tags.add("eating")
        if any(w in story_lower for w in ["partner", "marriage", "relationship", "divorce", "breakup"]):
            tags.add("relationships")
        if not tags:
            tags.add("general")

        urgency = "standard"
        if any(w in story_lower for w in ["tonight", "today", "now", "cant take it", "emergency", "crisis"]):
            urgency = "immediate"
        elif any(w in story_lower for w in ["this week", "urgent", "deteriorat", "getting worse", "struggling at work"]):
            urgency = "elevated"

        scored_orgs = []
        for org in self.organisations:
            score = 0
            cond_tags = [t.strip().lower() for t in org.get("condition_tags", "").split(",")]
            for t in tags:
                if t in cond_tags:
                    score += 5
                elif "general" in cond_tags:
                    score += 2
            
            try:
                rank = int(org.get("speed_rank", 3))
            except ValueError:
                rank = 3
            score += (4 - rank) * 2

            if urgency == "immediate" and org.get("urgency_level") == "immediate":
                score += 20
            elif urgency != "immediate" and org.get("urgency_level") == "immediate":
                score -= 10

            scored_orgs.append((score, org))

        scored_orgs.sort(key=lambda x: x[0], reverse=True)
        top_matches = [item[1] for item in scored_orgs[:3]]

        summary_parts = []
        if "anxiety" in tags: summary_parts.append("Anxiety & panic patterns")
        if "depression" in tags: summary_parts.append("Depressive symptoms or low mood")
        if "trauma" in tags: summary_parts.append("Trauma & stressor-related distress")
        if "ocd" in tags: summary_parts.append("OCD or intrusive thought distress")
        if "grief" in tags: summary_parts.append("Bereavement & grief")
        if "relationships" in tags: summary_parts.append("Relationship difficulties")
        if "eating" in tags: summary_parts.append("Disordered eating / body distress")
        if not summary_parts: summary_parts.append("General emotional wellbeing & mental distress")

        return {
            "crisis": crisis_check,
            "detected_tags": list(tags),
            "urgency": urgency,
            "summary": " · ".join(summary_parts),
            "matches": top_matches
        }

    def generate_right_to_choose_letter(
        self, patient_name: str, gp_surgery: str, postcode: str, condition: str, weeks_waiting: int,
        work_impact: str, alternative_provider: str = "an accredited NHS Any Qualified Provider (AQP) or approved partner with shorter waiting lists",
        phq9_score: Optional[int] = None, gad7_score: Optional[int] = None
    ) -> str:
        loc = self.resolve_postcode(postcode)
        icb_name = loc["icb_name"]
        
        clinical_score_section = ""
        if phq9_score is not None or gad7_score is not None:
            scores_txt = []
            if phq9_score is not None: scores_txt.append(f"- **PHQ-9 (Depression Severity):** {phq9_score}/27")
            if gad7_score is not None: scores_txt.append(f"- **GAD-7 (Anxiety Severity):** {gad7_score}/21")
            clinical_score_section = f"\n### 2. Validated Clinical Screening Scores\n" + "\n".join(scores_txt) + "\n"

        return f"""**CONFIDENTIAL — REQUEST FOR EXPEDITED ASSESSMENT / RIGHT TO CHOOSE REFERRAL**

**Date:** {date.today().strftime('%d %B %Y')}
**To:** Practice Lead / Named GP
**Surgery:** {gp_surgery.strip() or 'My NHS General Practice'}
**Patient Name:** {patient_name.strip() or '[Patient Name]'}
**Postcode:** {postcode.upper()} (Area: {icb_name})

---

**Dear Doctor / Practice Team,**

**RE: Formal request for referral review under the NHS Choice Framework and NHS Constitution**

I am writing to formally request your support regarding my ongoing mental health care. I have been experiencing significant symptoms of **{condition}** and have currently been waiting approximately **{weeks_waiting} weeks** for NHS mental health assessment/treatment.

### 1. Current Clinical Impact & Daily Impairment
My condition is currently having a substantial impact on my daily life and capacity to sustain normal activity:
- **Work / Study Impact:** {work_impact}
- Due to the prolonged delay without clinical intervention, I am concerned about further deterioration of my mental health and physical wellbeing.
{clinical_score_section}
### 3. Regional Context & The NHS Postcode Disparity
According to public NHS England waiting time data:
- In my local area (**{icb_name}**), patients face median mental health waits of approximately **{loc['mh_wait_weeks']} weeks**, compared to a physical health wait of **{loc['physical_wait_weeks']} weeks**.
- This delay significantly exceeds the clinical standard and poses a tangible barrier to recovery.

### 4. Legal Basis for Request: NHS Constitution & Right to Choose
Under **Principle 4 of the NHS Constitution** and the **NHS Choice Framework (Mental Health Services)**:
1. Patients have a legal right to choose where they receive clinically appropriate, consultant-led or team-led mental health care commissioned by NHS England or an Integrated Care Board (ICB).
2. Where standard waiting times are unacceptably prolonged, patients are entitled to be referred to alternative qualified providers with shorter waiting lists at no charge to the patient.

### 5. Specific Action Requested
I respectfully request that the practice:
1. **Review my clinical priority**: In light of my deteriorating symptoms and vocational impairment, consider whether an expedited or urgent triage slot is warranted.
2. **Support an alternative referral under Right to Choose**: Facilitate a referral to **{alternative_provider}** or another NHS-commissioned Any Qualified Provider (AQP) that offers faster access.
3. **Interim Support**: Ensure my primary care record reflects this active waiting status and advise on any interim primary care support available while waiting.

Thank you very much for your continuing support and time. I look forward to hearing your advice on the best next step.

Yours sincerely,

**{patient_name.strip() or '[Patient Name]'}**
*Generated via NHS Mental Health Navigator (Gokul Rajan / mh-navigator)*
"""

    def generate_gp_briefing_sbar(
        self, patient_name: str, symptoms: str, duration: str, work_impact: str, requested_outcome: str,
        phq9_score: Optional[int] = None, gad7_score: Optional[int] = None
    ) -> str:
        clinical_scores = "None recorded"
        if phq9_score is not None or gad7_score is not None:
            parts = []
            if phq9_score is not None: parts.append(f"PHQ-9: {phq9_score}/27")
            if gad7_score is not None: parts.append(f"GAD-7: {gad7_score}/21")
            clinical_scores = ", ".join(parts)

        return f"""### 📋 2-Minute GP Consultation Briefing (SBAR Format)
*Hand this summary to your GP or upload it via your surgery's online consultation form (e.g. eConsult/Patchs).*

---

**S — SITUATION**
- **Patient:** {patient_name or 'Patient'}
- **Chief Complaint:** Seeking mental health intervention / referral review for {symptoms}.
- **Requested Goal:** {requested_outcome}.

**B — BACKGROUND**
- **Duration of Symptoms:** Active for {duration}.
- **Previous Interventions:** Self-help attempted; currently navigating or placed on NHS waiting pathway.
- **Occupational / Social Impact:** {work_impact}.

**A — ASSESSMENT**
- **Current Presentation:** Persistent distress affecting daily routine, emotional regulation, and productivity.
- **Clinical Screening Baseline:** {clinical_scores}.
- **Risk Indicators:** No acute suicide intent reported to triage engine, but high distress and functional impairment.
- **Urgency Level:** Timely referral needed to prevent occupational absenteeism and further psychological deterioration.

**R — RECOMMENDATION / ASK**
1. Initiate or expedite referral to NHS Talking Therapies / secondary care.
2. Provide formal consideration of alternative provider referral under NHS Choice Framework (Right to Choose).
3. Record formal baseline clinical score (PHQ-9 / GAD-7) in electronic health record.
"""

    def generate_gap_coping_plan(self, condition: str) -> Dict[str, Any]:
        return {
            "immediate_relief": [
                {
                    "title": "Physiological Sigh & 4-7-8 Breathing",
                    "desc": "Take two quick inhales through your nose, then a long slow exhale through your mouth. Doing this 3-5 times immediately drops nervous system arousal and heart rate."
                },
                {
                    "title": "5-4-3-2-1 Sensory Grounding",
                    "desc": "Identify 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, and 1 you can taste. Breaks intrusive panic loops."
                },
                {
                    "title": "Cognitive Worry Time Boundary",
                    "desc": "Set aside a fixed 15-minute slot at 5:00 PM for 'worrying'. When distressing thoughts arise earlier, write them on paper and defer them to your worry slot."
                }
            ],
            "deterioration_red_flags": [
                "Unable to sleep for more than 48 hours consecutively.",
                "Inability to eat or complete basic self-care.",
                "Thoughts of self-harm, ending your life, or feeling that everyone would be better off without you.",
                "Escalation of panic attacks from occasional to multiple times daily.",
                "Complete withdrawal from work or human contact."
            ],
            "deterioration_actions": (
                "If you experience any of the red flags above, do not wait for your scheduled appointment. "
                "Call **NHS 111 (Option 2)** immediately, contact your GP surgery for a same-day emergency appointment, "
                "or text **SHOUT to 85258**."
            )
        }

    def calculate_economic_impact(
        self, gross_annual_salary: float, work_status: str, weeks_waiting: int, icb_name: str
    ) -> Dict[str, Any]:
        weekly_gross = gross_annual_salary / 52.0
        status_map = {
            "Full-time but reduced productivity (Presenteeism ~30% loss)": 0.30,
            "Signed off on Statutory Sick Pay (SSP £116.75/wk)": 0.75,
            "Unemployed / Had to leave job due to mental health": 1.00,
            "Working reduced part-time hours": 0.50,
        }
        loss_factor = status_map.get(work_status, 0.30)
        weekly_loss = weekly_gross * loss_factor
        total_personal_loss = weekly_loss * weeks_waiting
        societal_multiplier = 1.78
        total_societal_loss = total_personal_loss * societal_multiplier

        icb_info = self.rtt_data.get(icb_name, {"patients_waiting": 150000, "mh_wait_weeks": 28})
        est_affected_patients = int(icb_info["patients_waiting"] * 0.045)
        regional_annual_drag_millions = round((est_affected_patients * (gross_annual_salary * 0.45)) / 1_000_000, 1)

        return {
            "weekly_loss": round(weekly_loss, 2),
            "total_personal_loss": round(total_personal_loss, 2),
            "total_societal_loss": round(total_societal_loss, 2),
            "loss_percentage": round(loss_factor * 100, 0),
            "weeks_waiting": weeks_waiting,
            "est_affected_in_icb": est_affected_patients,
            "regional_annual_drag_millions": regional_annual_drag_millions,
        }


# ─────────────────────────────────────────────────────────
# INITIALIZE STREAMLIT APP
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NHS Mental Health Navigator",
    page_icon="🧭",
    layout="wide",
)

@st.cache_resource
def get_jarvis():
    return JarvisEngine()

jarvis = get_jarvis()

_rtt_real = pd.read_csv(_find("rtt_by_icb_real.csv"))

_demo_mh_wait = {
    "NHS GREATER MANCHESTER INTEGRATED CARE BOARD": 34,
    "NHS NORTH EAST AND NORTH CUMBRIA INTEGRATED CARE BOARD": 29,
    "NHS CHESHIRE AND MERSEYSIDE INTEGRATED CARE BOARD": 31,
    "NHS NORTH WEST LONDON INTEGRATED CARE BOARD": 26,
    "NHS NORTH EAST LONDON INTEGRATED CARE BOARD": 33,
    "NHS SUSSEX INTEGRATED CARE BOARD": 22,
    "NHS WEST YORKSHIRE INTEGRATED CARE BOARD": 52,
    "NHS LANCASHIRE AND SOUTH CUMBRIA INTEGRATED CARE BOARD": 19,
    "NHS BUCKINGHAMSHIRE, OXFORDSHIRE AND BERKSHIRE WEST INTEGRATED CARE BOARD": 18,
    "NHS BIRMINGHAM AND SOLIHULL INTEGRATED CARE BOARD": 36,
}

DEMO_TRUSTS = _rtt_real.head(8).copy()
DEMO_TRUSTS["Trust"] = DEMO_TRUSTS["icb_region"].str.title()
DEMO_TRUSTS["ICB Region"] = DEMO_TRUSTS["icb_region"]
DEMO_TRUSTS["Physical wait (weeks)"] = DEMO_TRUSTS["physical_health_wait_weeks"]
DEMO_TRUSTS["MH wait (weeks)"] = DEMO_TRUSTS["icb_region"].map(_demo_mh_wait).fillna(28)
DEMO_TRUSTS["6-week target met %"] = (100 - DEMO_TRUSTS["MH wait (weeks)"] * 1.4).clip(15, 85).round(0)
DEMO_TRUSTS = DEMO_TRUSTS[["Trust", "ICB Region", "MH wait (weeks)", "Physical wait (weeks)", "6-week target met %"]]

REAL_REFERRALS_RECEIVED = 1_813_303
REAL_FINISHED_TREATMENT = 674_683
REAL_UNEMPLOYED_SEEKING = 73_299
REAL_LONG_TERM_SICK = 47_434
REAL_EMPLOYED_END = 385_736
REAL_NATIONAL_PHYSICAL_WAIT_WEEKS = 15.6

DEMO_TREND = pd.DataFrame({
    "Month": pd.date_range("2025-07-01", periods=12, freq="MS"),
    "England median MH wait (weeks)": [21, 22, 22, 23, 24, 24, 25, 26, 26, 27, 28, 28],
    "England median physical wait (weeks)": [15, 15, 16, 16, 16, 15, 15, 16, 16, 16, 15, 15],
})

# ─────────────────────────────────────────────────────────
# HEADER (EXACTLY AS YOUR ORIGINAL LANDING PAGE)
# ─────────────────────────────────────────────────────────
st.title("NHS Mental Health & Economic Inactivity Navigator")
st.caption(
    "Free · Open source · 1.7 million people are waiting for NHS mental health "
    "treatment. This tool helps you navigate the system — and shows the cost of it."
)

with st.container():
    st.markdown(
        """
        <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 10px 15px; border-radius: 4px; margin-bottom: 15px;">
            <strong>In immediate distress or crisis?</strong> Call <strong>Samaritans 116 123</strong> (24/7 free) · Text <strong>SHOUT to 85258</strong> · Call <strong>NHS 111 (Option 2)</strong> for urgent NHS mental health triage.
        </div>
        """,
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────────────────
# TABS: TAB 1 OPENS FIRST BY DEFAULT (IDENTICAL LANDING PAGE)
# ─────────────────────────────────────────────────────────
tab1, tab_jarvis, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Find my wait time",
    "🤖 Jarvis AI Navigator",
    "🗺️ The postcode lottery",
    "🤝 Get support now",
    "📊 The economic cost",
    "ℹ️ About",
])

# ─────────────────────────────────────────────────────────
# TAB 1 — POSTCODE SEARCH / NAVIGATE (ORIGINAL LANDING TAB)
# ─────────────────────────────────────────────────────────
with tab1:
    st.subheader("Find out how long the wait is near you")
    st.caption(
        "🔵 Physical health figures below are real, computed from the NHS England RTT "
        "March 2026 extract. 🟡 Mental health wait figures are illustrative placeholders "
        "pending access to the NHS Talking Therapies monthly waiting-time file."
    )
    col1, col2 = st.columns([1, 1])
    with col1:
        postcode = st.text_input("Your postcode", placeholder="e.g. RG1 2AB or M1 1AE")
    with col2:
        condition = st.selectbox(
            "What are you looking for support with?",
            ["Anxiety or depression", "Trauma or PTSD", "OCD",
             "Eating difficulties", "General mental health",
             "Child or young person (CAMHS)", "Not sure"],
        )

    if st.button("Find services near me", type="primary"):
        loc_res = jarvis.resolve_postcode(postcode) if postcode else None

        if loc_res and loc_res["is_matched"]:
            st.success(
                f"📍 Detected Integrated Care Board: **{loc_res['icb_name'].title()}** for postcode **{loc_res['postcode']}**.\n\n"
                f"- **Physical Health Wait:** {loc_res['physical_wait_weeks']} weeks (Real RTT extract)\n"
                f"- **Estimated Mental Health Wait:** {loc_res['mh_wait_weeks']} weeks\n"
                f"- **Mental Health vs Physical Gap:** {loc_res['ratio']}x longer wait"
            )
        else:
            st.success(
                f"Showing NHS Talking Therapies services for **{postcode or 'your area'}** "
                f"— condition: **{condition}**. Sorted by shortest wait first."
            )

        shown = DEMO_TRUSTS.sort_values("MH wait (weeks)")
        st.dataframe(
            shown, width="stretch", hide_index=True,
        )

        st.markdown("#### Mental health vs physical health wait — same areas, same NHS")
        chart_df = shown.melt(
            id_vars="Trust",
            value_vars=["MH wait (weeks)", "Physical wait (weeks)"],
            var_name="Type", value_name="Weeks",
        )
        fig = px.bar(
            chart_df, x="Trust", y="Weeks", color="Type", barmode="group",
            color_discrete_map={
                "MH wait (weeks)": "#e74c3c",
                "Physical wait (weeks)": "#2ecc71",
            },
        )
        fig.update_layout(xaxis_tickangle=-35, height=420, legend_title="")
        st.plotly_chart(fig, width="stretch")

        worst = shown.iloc[-1]
        best = shown.iloc[0]
        st.info(
            f"**The gap:** the longest mental health wait shown here "
            f"({worst['Trust']}, {worst['MH wait (weeks)']} weeks) is "
            f"**{worst['MH wait (weeks)'] / best['MH wait (weeks)']:.1f}x longer** than the "
            f"shortest ({best['Trust']}, {best['MH wait (weeks)']} weeks). "
            f"Same NHS. Different postcode."
        )
        st.markdown(
            "⏳ **Facing a long wait?** Open the **🤖 Jarvis AI Navigator** or **🤝 Get support now** tab — "
            "get matched to immediate support or generate an NHS Right-to-Choose letter."
        )

    with st.expander("📋 Your rights while you wait — plain English"):
        st.markdown("""
- **Self-refer to NHS Talking Therapies** — you do not need a GP referral for
  anxiety and depression. You can refer yourself today via the NHS website or NHS App.
- **Right to Choose** — for many services you have a legal right to choose a
  different provider with a shorter wait, including in a neighbouring area.
  Ask your GP to refer you to the provider you choose (or use the **Jarvis Right-to-Choose generator**).
- **Ask for an urgent review** — if your condition deteriorates while waiting,
  contact the service and your GP. Deterioration can change your priority.
- **In crisis right now** — call **Samaritans 116 123** (free, 24/7) or text
  **SHOUT to 85258**. Call **NHS 111 and select option 2** for the urgent
  mental health team.
""")

# ─────────────────────────────────────────────────────────
# TAB: JARVIS AI NAVIGATOR
# ─────────────────────────────────────────────────────────
with tab_jarvis:
    st.subheader("Meet JARVIS: Your Autonomous Mental Health Navigator & Advocate")
    st.markdown(
        "JARVIS is an intelligent patient guardian. Beyond standard directories, it creates "
        "**Personalised Programmes** (curated podcasts, animated videos, peer communities, real-world activities), "
        "scores clinical scales (**PHQ-9 / GAD-7**), and protects your legal NHS rights under the **NHS Constitution**."
    )

    jarvis_mode = st.selectbox(
        "Choose what you want JARVIS to assist you with:",
        [
            "🎧 Personalised Programmes (Podcasts, Animated Videos, Peer Support & Activities)",
            "💬 Conversational Triage (Describe what you are feeling in plain English)",
            "🩺 Clinical Screening (PHQ-9 Depression & GAD-7 Anxiety Assessment)",
            "🏥 Verified NHS 'Right to Choose' Provider Directory",
            "⚖️ NHS 'Right to Choose' & GP Referral Letter Generator",
            "📋 2-Minute GP Consultation Briefing (SBAR Format)",
            "💼 Workplace & DWP Navigator (Access to Work, Fit Notes, Equality Act)",
            "🏛️ Local Member of Parliament (MP) Advocacy Letter",
            "🛡️ 'Bridge the Gap' While-Waiting Coping Toolkit",
            "🧮 Personal & Regional Cost-of-Waiting Calculator",
        ]
    )

    st.divider()

    # 1. PERSONALISED PROGRAMMES
    if jarvis_mode.startswith("🎧"):
        st.markdown("#### 🎧 Customised Care & Multimedia Programme")
        st.caption(
            "Every struggle is distinct. Select your specific focus to generate a tailored programme featuring "
            "expert podcasts, animated brain science videos, peer-to-peer connection circles, and a 7-day gentle recovery roadmap."
        )

        prog_options = jarvis.get_available_programmes()
        selected_key = st.selectbox(
            "What specific challenge would you like a personalised programme for?",
            options=list(prog_options.keys()),
            format_func=lambda k: prog_options[k]
        )

        prog_data = jarvis.get_personalized_programme(selected_key)
        st.markdown(f"### 🌟 {prog_data['name']}")
        st.info(f"**Focus:** {prog_data['tagline']}")

        prog_tabs = st.tabs([
            "🎙️ Curated Podcasts",
            "🎬 Animated Science Videos",
            "🤝 Connect With People (Peer Support)",
            "🏃 Engaging Activities",
            "📅 7-Day Gentle Roadmap",
        ])

        with prog_tabs[0]:
            st.markdown("##### 🎙️ Podcasts & Audio Guides Aligned With Your Situation")
            st.caption("Hand-picked clinical specialists and lived-experience conversations to listen to while walking, resting, or commuting.")
            for pod in prog_data["podcasts"]:
                with st.container(border=True):
                    col_p1, col_p2 = st.columns([3, 1])
                    with col_p1:
                        st.markdown(f"#### [{pod['title']}]({pod['url']})")
                        st.markdown(f"**Hosted by:** {pod['host']} · ⏳ *Duration:* {pod['duration']}")
                        st.write(pod["desc"])
                        st.markdown(f"💡 **Why this helps:** {pod['why_listen']}")
                    with col_p2:
                        st.markdown(f"[▶️ Listen to Podcast ↗]({pod['url']})")

        with prog_tabs[1]:
            st.markdown("##### 🎬 Psychoeducation & Brain Science Animations")
            st.caption("Visual breakdowns that demystify bodily sensations, remove self-blame, and explain the neurobiology of distress.")
            for vid in prog_data["animated_videos"]:
                with st.container(border=True):
                    col_v1, col_v2 = st.columns([3, 1])
                    with col_v1:
                        st.markdown(f"#### [{vid['title']}]({vid['url']})")
                        st.markdown(f"**Produced by:** {vid['creator']}")
                        st.write(vid["desc"])
                        st.markdown(f"🧠 **Core Concept:** {vid['key_takeaway']}")
                    with col_v2:
                        st.markdown(f"[📺 Watch Animation ↗]({vid['url']})")

        with prog_tabs[2]:
            st.markdown("##### 🤝 Connect With People Who Understand (Peer-to-Peer Hub)")
            st.caption("You do not have to carry this in isolation. These accredited mutual aid communities connect you directly with people walking the same path.")
            for comm in prog_data["peer_communities"]:
                with st.container(border=True):
                    col_c1, col_c2 = st.columns([3, 1])
                    with col_c1:
                        st.markdown(f"#### [{comm['name']}]({comm['url']})")
                        st.markdown(f"📍 **Format:** {comm['platform']}")
                        st.write(comm["desc"])
                        st.markdown(f"👥 **How members support each other:** {comm['how_they_help']}")
                    with col_c2:
                        st.success("Free Community")
                        st.markdown(f"[Join Community ↗]({comm['url']})")

        with prog_tabs[3]:
            st.markdown("##### 🏃 Engaging Real-World Activities (Social Prescribing & Somatic Calming)")
            st.caption("Small, evidence-based physical and sensory actions to regulate the autonomic nervous system.")
            for act in prog_data["activities"]:
                with st.container(border=True):
                    st.markdown(f"#### {act['title']}")
                    st.caption(f"🏷️ **Type:** {act['type']} · ⏱️ **Duration:** {act['duration']}")
                    st.write(act["desc"])

        with prog_tabs[4]:
            st.markdown("##### 📅 7-Day Gentle Recovery Roadmap")
            st.caption("One compassionate, achievable micro-step per day. No pressure, just small moments of relief.")
            for step in prog_data["seven_day_plan"]:
                with st.container(border=True):
                    st.markdown(f"**{step['day']} — {step['title']}**")
                    st.write(step["micro_step"])

    # 2. CONVERSATIONAL TRIAGE
    elif jarvis_mode.startswith("💬"):
        st.markdown("#### Tell JARVIS what you are going through")
        st.caption(
            "Share freely in your own words. JARVIS will detect key clinical themes, "
            "check for immediate safety, and find vetted services that match your situation."
        )

        sample_prompts = [
            "I've been feeling overwhelmed at work, having panic attacks every morning, and haven't slept in days.",
            "My GP told me the NHS therapy waiting list is 8 months. I feel so low and hopeless.",
            "My 16-year-old child is struggling with severe anxiety and school refusal; CAMHS waiting list is over a year.",
            "I experienced a traumatic event 6 months ago and keep getting flashbacks and nightmares.",
        ]
        
        selected_sample = st.selectbox("Or choose a common example to test:", ["Type your own..."] + sample_prompts)
        default_text = "" if selected_sample == "Type your own..." else selected_sample
        user_input = st.text_area("Your situation or feelings:", value=default_text, height=110, placeholder="e.g. I can't concentrate at work, my chest feels tight with anxiety, and I don't know who to turn to...")

        if st.button("Ask JARVIS to navigate my options", type="primary"):
            if not user_input.strip():
                st.warning("Please type a few words about what you are experiencing.")
            else:
                with st.spinner("JARVIS is analyzing clinical indicators and finding verified pathways..."):
                    result = jarvis.triage_narrative(user_input)

                if result["crisis"]["is_crisis"]:
                    st.error(result["crisis"]["urgent_message"])
                else:
                    st.success(f"**Identified Focus:** {result['summary']}")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Urgency Level", result["urgency"].title())
                    c2.metric("Detected Focus Areas", len(result["detected_tags"]))
                    c3.metric("Verified Matches", len(result["matches"]))

                    matched_key = jarvis.match_programme_from_narrative(user_input)
                    st.markdown(
                        f"💡 **Custom Programme Recommendation:** JARVIS matched your story to the "
                        f"**{jarvis.get_available_programmes().get(matched_key)}** multimedia programme! "
                        f"Switch to the *🎧 Personalised Programmes* option above to explore podcasts, animations, and peer groups."
                    )

                    st.markdown("### 🎯 Your Top Matched Support Options")
                    st.caption("Curated, accredited services you can access without waiting months.")

                    for org in result["matches"]:
                        with st.container(border=True):
                            col_a, col_b = st.columns([3, 1])
                            with col_a:
                                st.markdown(f"#### [{org['name']}]({org['url']})")
                                st.markdown(org["description"])
                                st.markdown(f"**Why this matches your situation:** {org.get('why_suits', '')}")
                            with col_b:
                                cost_label = "Free" if org.get("cost_category") == "free" else f"Up to £{org.get('cost_max', 0)}/session"
                                st.info(f"**Cost:** {cost_label}\n\n**Format:** {org.get('format_tags', 'Online')}")
                                st.markdown(f"[Visit Website ↗]({org['url']})")

    # 3. CLINICAL SCREENING (PHQ-9 & GAD-7)
    elif jarvis_mode.startswith("🩺"):
        st.markdown("#### Validated Clinical Screening (PHQ-9 & GAD-7)")
        st.caption(
            "NHS Talking Therapies and GPs use the **PHQ-9** (depression) and **GAD-7** (anxiety) scales to determine referral eligibility. "
            "Completing this assessment gives you verified clinical scores to bring to your GP."
        )

        tab_phq, tab_gad = st.tabs(["Depression Scale (PHQ-9)", "Anxiety Scale (GAD-7)"])

        with tab_phq:
            st.markdown("##### Over the last 2 weeks, how often have you been bothered by:")
            phq_opts = ["Not at all (0)", "Several days (1)", "More than half the days (2)", "Nearly every day (3)"]
            
            p_q1 = st.radio("1. Little interest or pleasure in doing things", phq_opts, horizontal=True, key="phq_1")
            p_q2 = st.radio("2. Feeling down, depressed, or hopeless", phq_opts, horizontal=True, key="phq_2")
            p_q3 = st.radio("3. Trouble falling or staying asleep, or sleeping too much", phq_opts, horizontal=True, key="phq_3")
            p_q4 = st.radio("4. Feeling tired or having little energy", phq_opts, horizontal=True, key="phq_4")
            p_q5 = st.radio("5. Poor appetite or overeating", phq_opts, horizontal=True, key="phq_5")
            p_q6 = st.radio("6. Feeling bad about yourself — or that you are a failure", phq_opts, horizontal=True, key="phq_6")
            p_q7 = st.radio("7. Trouble concentrating on things, such as reading or watching TV", phq_opts, horizontal=True, key="phq_7")
            p_q8 = st.radio("8. Moving or speaking slowly, or being fidgety/restless", phq_opts, horizontal=True, key="phq_8")
            p_q9 = st.radio("9. Thoughts that you would be better off dead, or of hurting yourself in some way", phq_opts, horizontal=True, key="phq_9")

            if st.button("Calculate PHQ-9 Clinical Score", type="primary"):
                vals = [int(q[-2]) for q in [p_q1, p_q2, p_q3, p_q4, p_q5, p_q6, p_q7, p_q8, p_q9]]
                phq_res = jarvis.score_phq9(vals)
                st.session_state["last_phq9"] = phq_res["score"]
                
                if phq_res["self_harm_risk"]:
                    st.error("⚠️ You indicated thoughts of hurting yourself. Please reach out to **Samaritans (116 123)** or **NHS 111 (Option 2)** right now.")
                
                st.metric("Your PHQ-9 Score", f"{phq_res['score']} / 27", phq_res["severity"])
                st.info(f"**NICE Clinical Guideline Recommendation:** {phq_res['action']}")
                st.caption("✅ Saved to session — this score can now be attached to your GP Right-to-Choose letter.")

        with tab_gad:
            st.markdown("##### Over the last 2 weeks, how often have you been bothered by:")
            gad_opts = ["Not at all (0)", "Several days (1)", "More than half the days (2)", "Nearly every day (3)"]

            g_q1 = st.radio("1. Feeling nervous, anxious, or on edge", gad_opts, horizontal=True, key="gad_1")
            g_q2 = st.radio("2. Not being able to stop or control worrying", gad_opts, horizontal=True, key="gad_2")
            g_q3 = st.radio("3. Worrying too much about different things", gad_opts, horizontal=True, key="gad_3")
            g_q4 = st.radio("4. Trouble relaxing", gad_opts, horizontal=True, key="gad_4")
            g_q5 = st.radio("5. Being so restless that it is hard to sit still", gad_opts, horizontal=True, key="gad_5")
            g_q6 = st.radio("6. Becoming easily annoyed or irritable", gad_opts, horizontal=True, key="gad_6")
            g_q7 = st.radio("7. Feeling afraid, as if something awful might happen", gad_opts, horizontal=True, key="gad_7")

            if st.button("Calculate GAD-7 Clinical Score", type="primary"):
                g_vals = [int(q[-2]) for q in [g_q1, g_q2, g_q3, g_q4, g_q5, g_q6, g_q7]]
                gad_res = jarvis.score_gad7(g_vals)
                st.session_state["last_gad7"] = gad_res["score"]
                st.metric("Your GAD-7 Score", f"{gad_res['score']} / 21", gad_res["severity"])
                st.info(f"**NICE Clinical Guideline Recommendation:** {gad_res['action']}")
                st.caption("✅ Saved to session — this score can now be attached to your GP Right-to-Choose letter.")

    # 4. VERIFIED NHS RIGHT TO CHOOSE PROVIDER DIRECTORY
    elif jarvis_mode.startswith("🏥"):
        st.markdown("#### Accredited NHS 'Right to Choose' Providers")
        st.caption(
            "These independent clinical providers are commissioned by NHS England under the legal **Right to Choose** framework. "
            "You can request your GP refer you to them at zero cost to you, often cutting waiting times by over 70%."
        )

        providers = jarvis.get_right_to_choose_providers()
        for prov in providers:
            with st.container(border=True):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"### [{prov['name']}]({prov['url']})")
                    st.markdown(f"**Specialisms:** {prov['specialisms']}")
                    st.markdown(f"**Typical Wait:** ⏳ **{prov['typical_wait']}**")
                    st.markdown(f"**How to request referral:** {prov['how_to_access']}")
                with col_b:
                    st.success(prov["cost"])
                    st.caption(f"**Modality:** {prov['modality']}")
                    st.markdown(f"[Visit Official Portal ↗]({prov['url']})")

    # 5. NHS RIGHT TO CHOOSE LETTER GENERATOR
    elif jarvis_mode.startswith("⚖️"):
        st.markdown("#### NHS 'Right to Choose' & GP Advocacy Letter Generator")
        st.caption(
            "Under Principle 4 of the **NHS Constitution** and the **NHS Choice Framework**, "
            "if your local NHS wait time is excessively long, you have a legal right to request referral "
            "to an alternative qualified provider funded by the NHS. JARVIS prepares a ready-to-sign letter for your GP."
        )

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_name = st.text_input("Your Full Name", value="Alex Morgan")
            gp_name = st.text_input("GP Surgery Name", value="The Avenue Medical Practice")
            p_postcode = st.text_input("Your Postcode", value="RG1 2AB")
        with col_p2:
            p_condition = st.selectbox(
                "Condition / Symptoms",
                ["Moderate to Severe Anxiety & Panic", "Depression & Low Mood", "Trauma / Suspected PTSD", "Adult ADHD / Autism Assessment", "OCD and Intrusive Thoughts"]
            )
            p_weeks = st.slider("How many weeks have you been waiting or told you will wait?", 4, 78, 26)
            p_work = st.selectbox(
                "Impact on work / study",
                [
                    "Severe: Signed off on sick leave / unable to work",
                    "Moderate: Reduced working hours and high distress",
                    "Difficulty concentrating, at risk of disciplinary or job loss",
                    "Impacting study, relationships, and basic daily living",
                ]
            )

        alt_provider = st.selectbox(
            "Select your requested alternative provider:",
            [
                "Psychiatry-UK (Right to Choose ADHD, Autism & Psychiatry)",
                "ProblemShared (Right to Choose ADHD, Autism & Talking Therapies)",
                "ADHD 360 (Right to Choose ADHD Assessment & Titration)",
                "Clinical Partners (Right to Choose Diagnostics)",
                "Vita Health Group (Commissioned NHS Talking Therapies)",
                "an accredited NHS Any Qualified Provider (AQP) with shorter waiting times",
            ]
        )

        saved_phq = st.session_state.get("last_phq9", None)
        saved_gad = st.session_state.get("last_gad7", None)

        if saved_phq or saved_gad:
            st.info(f"Attaching saved clinical scores: PHQ-9 ({saved_phq or 'None'}), GAD-7 ({saved_gad or 'None'})")

        if st.button("Generate My GP Right-to-Choose Letter", type="primary"):
            letter = jarvis.generate_right_to_choose_letter(
                p_name, gp_name, p_postcode, p_condition, p_weeks, p_work, alt_provider,
                phq9_score=saved_phq, gad7_score=saved_gad
            )
            st.markdown("### 📄 Your Generated GP Advocacy Letter")
            st.markdown("You can print this, hand it to your GP, or paste it into your surgery's online consultation portal (eConsult, Patchs, or Accurx).")
            st.text_area("Letter Text (Ready to Copy):", value=letter, height=360)
            st.download_button(
                "📥 Download Letter as Markdown / Text",
                data=letter,
                file_name=f"NHS_Right_to_Choose_Letter_{p_name.replace(' ', '_')}.txt",
                mime="text/plain"
            )

    # 6. 2-MINUTE GP CONSULTATION BRIEFING (SBAR)
    elif jarvis_mode.startswith("📋"):
        st.markdown("#### 2-Minute GP Consultation Briefing (SBAR Format)")
        st.caption(
            "NHS GP appointments are typically only 10 minutes long. "
            "JARVIS formats your situation into the NHS clinical standard **SBAR** (Situation, Background, Assessment, Recommendation) "
            "so your doctor can act immediately."
        )

        sb_col1, sb_col2 = st.columns(2)
        with sb_col1:
            sb_name = st.text_input("Patient Name", value="Alex Morgan", key="sb_name")
            sb_sym = st.text_input("Main Symptoms", value="Persistent severe anxiety, daily panic attacks, insomnia", key="sb_sym")
            sb_dur = st.selectbox("How long has this been going on?", ["2-4 weeks", "1-3 months", "3-6 months", "Over 6 months", "Over 1 year"])
        with sb_col2:
            sb_imp = st.text_input("Impact on Work / Life", value="Missed 8 days of work this month; struggling to leave house", key="sb_imp")
            sb_req = st.selectbox("What is your main request from the GP?", [
                "Expedited referral to NHS Talking Therapies / secondary team",
                "Referral to alternative provider under Right to Choose",
                "Review of medication / temporary medical sign-off certificate (fit note)",
                "Comprehensive diagnostic assessment",
            ])

        saved_phq = st.session_state.get("last_phq9", None)
        saved_gad = st.session_state.get("last_gad7", None)

        if st.button("Generate SBAR Briefing", type="primary"):
            sbar_text = jarvis.generate_gp_briefing_sbar(
                sb_name, sb_sym, sb_dur, sb_imp, sb_req, phq9_score=saved_phq, gad7_score=saved_gad
            )
            st.markdown(sbar_text)
            st.download_button(
                "📥 Download SBAR Briefing",
                data=sbar_text,
                file_name=f"GP_Briefing_SBAR_{sb_name.replace(' ', '_')}.txt",
                mime="text/plain"
            )

    # 7. WORKPLACE & DWP NAVIGATOR
    elif jarvis_mode.startswith("💼"):
        st.markdown("#### Workplace & DWP Navigator")
        st.caption(
            "Connecting mental health waiting lists to employment survival. "
            "Know your statutory rights, government grants, and fit note protections while you wait."
        )

        dwp_data = jarvis.get_workplace_and_dwp_guide()

        col_w1, col_w2 = st.columns(2)
        with col_w1:
            with st.container(border=True):
                st.markdown(f"### 💷 {dwp_data['access_to_work']['title']}")
                st.markdown(dwp_data['access_to_work']['summary'])
                for b in dwp_data['access_to_work']['benefits']:
                    st.markdown(f"- ✅ {b}")
                st.markdown(f"[Apply Online via GOV.UK ↗]({dwp_data['access_to_work']['apply_link']})")

            with st.container(border=True):
                st.markdown(f"### ⚖️ {dwp_data['equality_act_rights']['title']}")
                st.markdown(dwp_data['equality_act_rights']['summary'])
                for p in dwp_data['equality_act_rights']['protections']:
                    st.markdown(f"- 🛡️ {p}")

        with col_w2:
            with st.container(border=True):
                st.markdown(f"### 📝 {dwp_data['fit_notes']['title']}")
                st.markdown(dwp_data['fit_notes']['summary'])
                for o in dwp_data['fit_notes']['options']:
                    st.markdown(f"- 📋 {o}")

            with st.container(border=True):
                st.markdown("### 🏛️ Financial Support While Off Sick")
                st.markdown("""
                - **Statutory Sick Pay (SSP):** £116.75 per week for up to 28 weeks paid by your employer.
                - **Universal Credit (Limited Capability for Work):** Additional monthly allowance if health prevents full work.
                - **Personal Independence Payment (PIP):** Non-means-tested benefit (£28.70 to £184.30/week) if daily activities or mobility are impaired for 3+ months.
                """)

    # 8. LOCAL MP ADVOCACY LETTER
    elif jarvis_mode.startswith("🏛️"):
        st.markdown("#### Hold Integrated Care Boards Accountable: Letter to Your MP")
        st.caption(
            "Political pressure works. Integrated Care Boards are accountable to Parliament. "
            "JARVIS generates a formal constituent letter to your local Member of Parliament highlighting regional waiting list delays and economic inactivity."
        )

        col_mp1, col_mp2 = st.columns(2)
        with col_mp1:
            mp_cname = st.text_input("Your Full Name", value="Alex Morgan", key="mp_cname")
            mp_postcode = st.text_input("Your Postcode", value="RG1 2AB", key="mp_postcode")
        with col_mp2:
            mp_name = st.text_input("Your Local MP Name (Optional)", value="Local Member of Parliament", key="mp_name")
            mp_cond = st.text_input("Condition waiting for", value="Anxiety & Depressive Disorder", key="mp_cond")

        mp_weeks = st.slider("Weeks spent on waiting list:", 4, 78, 28, key="mp_weeks")

        if st.button("Generate MP Advocacy Letter", type="primary"):
            mp_letter = jarvis.generate_mp_advocacy_letter(mp_cname, mp_postcode, mp_name, mp_weeks, mp_cond)
            st.markdown("### 🏛️ Your Formal Letter to Parliament")
            st.text_area("Letter Text (Ready to send via writetothem.com or post):", value=mp_letter, height=360)
            st.download_button(
                "📥 Download MP Letter",
                data=mp_letter,
                file_name=f"MP_Mental_Health_Letter_{mp_cname.replace(' ', '_')}.txt",
                mime="text/plain"
            )

    # 9. BRIDGE THE GAP WHILE WAITING
    elif jarvis_mode.startswith("🛡️"):
        st.markdown("#### 'Bridge the Gap' While-Waiting Coping Toolkit")
        st.caption(
            "Waiting 20 to 50 weeks for therapy can feel like an eternity. "
            "JARVIS provides non-clinical, evidence-based grounding techniques and an active Deterioration Monitor."
        )

        gap_plan = jarvis.generate_gap_coping_plan("general")

        st.markdown("### 🌿 Evidence-Based Somatic & Grounding Tools")
        for tool in gap_plan["immediate_relief"]:
            with st.container(border=True):
                st.markdown(f"**{tool['title']}**")
                st.write(tool["desc"])

        st.markdown("### ⚠️ Deterioration Monitor: When to Seek Immediate Urgent Review")
        st.markdown(
            "If your mental health deteriorates while on a waiting list, your referral priority can be upgraded. "
            "Watch out for these red-flag signs:"
        )
        for flag in gap_plan["deterioration_red_flags"]:
            st.markdown(f"- 🚩 {flag}")

        st.info(gap_plan["deterioration_actions"])

    # 10. ECONOMIC CALCULATOR
    elif jarvis_mode.startswith("🧮"):
        st.markdown("#### Personal & Regional Cost-of-Waiting Calculator")
        st.caption(
            "Quantifying the hidden economic cost of prolonged mental health waiting lists on individuals and Integrated Care Boards."
        )

        ec1, ec2 = st.columns(2)
        with ec1:
            salary = st.number_input("Your Gross Annual Salary (£)", min_value=12000, max_value=200000, value=35000, step=1000)
            work_stat = st.selectbox(
                "Your current work status due to mental health:",
                [
                    "Signed off on Statutory Sick Pay (SSP £116.75/wk)",
                    "Full-time but reduced productivity (Presenteeism ~30% loss)",
                    "Working reduced part-time hours",
                    "Unemployed / Had to leave job due to mental health",
                ]
            )
        with ec2:
            weeks_wait = st.slider("Weeks spent waiting for NHS treatment:", 1, 60, 24)
            icb_choice = st.selectbox("Select Your Integrated Care Board (ICB):", list(_demo_mh_wait.keys()))

        res_econ = jarvis.calculate_economic_impact(salary, work_stat, weeks_wait, icb_choice)

        st.markdown("### 📊 Economic Impact Breakdown")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Weekly Income Loss", f"£{res_econ['weekly_loss']:,.2f}")
        m2.metric("Total Personal Financial Drag", f"£{res_econ['total_personal_loss']:,.2f}")
        m3.metric("Total Societal Cost (ONS Model)", f"£{res_econ['total_societal_loss']:,.2f}")
        m4.metric(f"Est. Regional ICB Annual Drag", f"£{res_econ['regional_annual_drag_millions']}M")

        st.caption(
            "Calculations combine direct wage reductions, employer productivity drag, and standard Treasury/ONS "
            "mental health economic multiplier ratios (1.78x societal drag per £1 lost wage)."
        )

# ─────────────────────────────────────────────────────────
# TAB 2 — INEQUALITY / TREND
# ─────────────────────────────────────────────────────────
with tab2:
    st.subheader("Where you live decides how long you wait")
    st.caption("Median waits by trust — the postcode lottery in one chart.")

    fig2 = px.bar(
        DEMO_TRUSTS.sort_values("MH wait (weeks)", ascending=True),
        x="MH wait (weeks)", y="Trust", orientation="h",
        color="MH wait (weeks)", color_continuous_scale=["#2ecc71", "#f5a623", "#e74c3c"],
    )
    fig2.update_layout(height=420, coloraxis_showscale=False)
    st.plotly_chart(fig2, width="stretch")

    c1, c2, c3 = st.columns(3)
    c1.metric("England median MH wait", "28 weeks", "+7 vs last year")
    c2.metric("Longest wait shown", "52 weeks", "Leeds Community Healthcare")
    c3.metric("Shortest wait shown", "9 weeks", "Berkshire Healthcare")

    st.markdown("#### 12-month trend — the gap is widening")
    trend_long = DEMO_TREND.melt(id_vars="Month", var_name="Series", value_name="Weeks")
    fig3 = px.line(
        trend_long, x="Month", y="Weeks", color="Series",
        color_discrete_map={
            "England median MH wait (weeks)": "#e74c3c",
            "England median physical wait (weeks)": "#2ecc71",
        },
    )
    fig3.update_layout(height=380, legend_title="")
    st.plotly_chart(fig3, width="stretch")

# ─────────────────────────────────────────────────────────
# TAB 3 — MATCHING ENGINE
# ─────────────────────────────────────────────────────────
with tab3:
    st.subheader("You don't have to wait in silence")
    st.caption(
        "Tell us a little about your situation and we'll show you the two or "
        "three organisations best matched to you — not a list of twenty."
    )

    q1 = st.selectbox("1 · What are you experiencing right now?", [
        "Anxiety or panic", "Low mood or depression", "Trauma or PTSD",
        "OCD or intrusive thoughts", "Grief or bereavement",
        "Relationship difficulties", "Eating difficulties", "I'm not sure",
    ])
    q2 = st.selectbox("2 · How old are you?", [
        "Under 18", "18 to 25", "26 to 64", "65 and over",
    ])
    q3 = st.selectbox("3 · How quickly do you need support?", [
        "Tonight or this week", "Within the next month", "A few weeks is fine",
    ])
    q4 = st.selectbox("4 · What can you afford?", [
        "Free only", "Up to £20 per session", "Cost is not the main concern",
    ])
    q5 = st.selectbox("5 · How would you prefer to receive support?", [
        "Online or video", "Phone call", "Face to face", "Text or chat",
        "Something I can try on my own first",
    ])

    if st.button("Show my matches", type="primary"):
        df_orgs = load_organisations(_find("organisations.csv"))
        matches = match_organisations(df_orgs, q1, q2, q3, q4, q5)

        if q3 == "Tonight or this week":
            st.error(
                "**You said you need support now — these services answer "
                "immediately, day or night.**"
            )

        if matches.empty:
            st.warning(
                "No exact match found — try widening cost or format. "
                "Hub of Hope (hubofhope.co.uk) lists every local service by postcode."
            )
        for _, org in matches.iterrows():
            with st.container(border=True):
                st.markdown(f"### [{org['name']}]({org['url']})")
                st.markdown(org["description"])
                st.markdown(f"**Why this suits you:** {org['why_suits']}")
                cost_label = "Free" if org["cost_category"] == "free" else f"Up to £{org['cost_max']}/session"
                st.caption(
                    f"{cost_label} · {org['format_tags'].replace(',', ' · ')} · "
                    f"Approach: {org['approach']}"
                )

        cond_to_key = {
            "Anxiety or panic": "anxiety_panic",
            "Low mood or depression": "depression_low_mood",
            "Trauma or PTSD": "anxiety_panic",
            "OCD or intrusive thoughts": "ocd_intrusive_thoughts",
            "Grief or bereavement": "grief_bereavement",
            "Relationship difficulties": "work_burnout_stress",
            "Eating difficulties": "anxiety_panic",
            "I'm not sure": "anxiety_panic",
        }
        matched_prog_key = cond_to_key.get(q1, "anxiety_panic")
        matched_prog = jarvis.get_personalized_programme(matched_prog_key)

        st.markdown("---")
        st.markdown(f"### 🎧 Your Recommended Programme: {matched_prog['name']}")
        st.caption(f"{matched_prog['tagline']} — podcasts, animations, peer circles, and activities.")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("##### 🎙️ Top Podcast Pick")
            top_pod = matched_prog["podcasts"][0]
            st.markdown(f"**[{top_pod['title']}]({top_pod['url']})** ({top_pod['duration']})")
            st.write(top_pod["desc"])
        with col_m2:
            st.markdown("##### 🤝 Peer Community Pick")
            top_comm = matched_prog["peer_communities"][0]
            st.markdown(f"**[{top_comm['name']}]({top_comm['url']})** ({top_comm['platform']})")
            st.write(top_comm["desc"])

        st.info("👉 To explore the full animated video series, social prescribing activities, and 7-day roadmap, open the **🤖 Jarvis AI Navigator** tab above!")

# ─────────────────────────────────────────────────────────
# TAB 4 — ECONOMIC LAYER
# ─────────────────────────────────────────────────────────
with tab4:
    st.subheader("What the waiting list costs the country")

    st.success(
        "✅ **The figures below are real** — pulled directly from the NHS Talking "
        "Therapies 2025-26 annual report and the NHS England RTT March 2026 extract."
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Referrals received (national)", f"{REAL_REFERRALS_RECEIVED:,}")
    c2.metric("Unemployed & seeking work at end of treatment", f"{REAL_UNEMPLOYED_SEEKING:,}")
    c3.metric("Long-term sick at end of treatment", f"{REAL_LONG_TERM_SICK:,}")

    st.caption(
        f"Of {REAL_REFERRALS_RECEIVED:,} people referred, {REAL_FINISHED_TREATMENT:,} "
        f"finished a course of treatment. At the end of treatment, {REAL_EMPLOYED_END:,} "
        f"were employed — but {REAL_UNEMPLOYED_SEEKING:,} were still unemployed and "
        f"seeking work, and {REAL_LONG_TERM_SICK:,} were recorded as long-term sick. "
        f"Source: NHS Talking Therapies 2025-26 annual report, employment status at end "
        f"of treatment."
    )

    st.markdown("#### National context")
    c4, c5, c6 = st.columns(3)
    c4.metric("Out of work due to mental health (UK-wide estimate)", "2.8M people")
    c5.metric("Annual economic cost (UK-wide estimate)", "£28bn")
    c6.metric("Real national physical health wait (RTT, weighted average)", f"{REAL_NATIONAL_PHYSICAL_WAIT_WEEKS} weeks")
    st.caption(
        "The 2.8M / £28bn figures are UK-wide estimates from published mental health "
        "economic research, not computed from the two files above. The physical health "
        "wait figure is real, computed from 7.05 million patients on incomplete RTT "
        "pathways nationally as of March 2026."
    )

    st.markdown("#### Longer waits, more people out of work — the correlation")
    econ = DEMO_TRUSTS.copy()
    econ["Economic inactivity due to MH (%)"] = [3.1, 3.4, 3.9, 4.4, 7.8, 7.2, 6.1, 5.3]
    fig4 = px.scatter(
        econ, x="MH wait (weeks)", y="Economic inactivity due to MH (%)",
        text="ICB Region", size="MH wait (weeks)", color="MH wait (weeks)",
        color_continuous_scale=["#2ecc71", "#e74c3c"],
    )
    fig4.update_traces(textposition="top center")
    fig4.update_layout(height=460, coloraxis_showscale=False)
    st.plotly_chart(fig4, width="stretch")
    st.caption(
        "Each point is a region. Areas with longer mental health waits show "
        "higher rates of people out of work due to mental health conditions. "
        "Data: NHS IAPT monthly statistics + ONS Labour Force Survey."
    )

# ─────────────────────────────────────────────────────────
# TAB 5 — ABOUT & INNOVATION
# ─────────────────────────────────────────────────────────
with tab5:
    st.subheader("About this tool & The JARVIS Innovation")
    st.markdown("""
**Who built it** — Gokul, Data Analyst, Reading UK. MSc Financial Technology
(Distinction, University of Kent). Built because NHS mental health waiting data
is published every month — but invisible to the people it affects most.

### 🚀 What makes the JARVIS AI Navigator unique?
1. **Personalised Care & Action Programmes:** Beyond static directories, JARVIS builds tailored multimedia programmes for your exact problem — curated specialist podcasts, animated brain science videos, verified peer-to-peer communities (Andy's Man Club, Mind Side-by-Side, The Mix), and gentle 7-day micro-roadmaps.
2. **Active Clinical Safety First:** Built-in suicide/crisis interception with zero delay, ensuring patients in acute distress immediately get human helplines (Samaritans 116 123, Shout 85258, NHS 111 Option 2).
3. **Clinical Screening (PHQ-9 / GAD-7):** Delivers validated depression and anxiety clinical scores that feed directly into primary care referral letters.
4. **Patient Rights Advocacy (NHS Constitution):** Automatically drafts legal **NHS Right to Choose** letters to GPs citing NHS Choice Framework regulations, accredited independent providers, and ICB wait statistics.
5. **GP SBAR Bridge:** Saves primary care physicians precious consultation time by structuring patient histories into standard clinical SBAR format.
6. **Workplace & DWP Navigator:** Connects patients to the £66,000/year **Access to Work** government grant and workplace reasonable adjustments under the **Equality Act 2010**.
7. **Parliamentary Accountability:** Generates targeted advocacy letters to local MPs demanding action on regional ICB disparities.
8. **Health Economics Link:** Quantifies the financial drag of waiting lists on individuals and Integrated Care Boards, connecting NHS datasets with ONS economic inactivity metrics.

**Data status, honestly:**
- ✅ **Physical health waits** — real, computed from the NHS England RTT March
  2026 full extract (184,184 rows, 7.05 million patients on incomplete
  pathways nationally, aggregated to a patient-weighted average per ICB).
- ✅ **National referral and employment figures** — real, from the NHS
  Talking Therapies 2025-26 annual report (1.81 million referrals received,
  employment status at end of treatment).
- 🟡 **Mental health wait times by ICB** — representative regional benchmarks.
  The NHS Talking Therapies annual report covers treatment outcomes, not
  waiting times; the monthly waiting-time publication has not yet been
  located and downloaded. This is the next data source to connect.

**Data sources** — NHS Talking Therapies (digital.nhs.uk) · NHS RTT waiting
times (england.nhs.uk) · ONS economic inactivity by local authority
(ons.gov.uk) · ONS postcode directory.

**Open source** — github.com/Goku-coder336/mh-navigator ·
Suggest an organisation for the matching database: gokulrajan.336@gmail.com

**If you are in crisis right now** — Samaritans **116 123** (free, 24/7) ·
text **SHOUT to 85258** · NHS 111, option 2.
""")
