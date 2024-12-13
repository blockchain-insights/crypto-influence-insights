<div style="display: flex; align-items: center;">
  <img src="docs/subnet_logo.png" alt="subnet_logo" style="width: 200px; height: 60px; margin-right: 10px;">
  <h1 style="margin: 0;">Crypto Influence Insights Subnet</h1>
</div>

## Table of Contents
 
- [Introduction](#introduction)
- [Subnet Vision](#subnet-vision)
- [Roadmap](#roadmap)
- [Overview](#overview)
- [Subnet Architecture Components](#subnet-architecture-components)
- [Scoring](#scoring)
- [Miner Setup](MINER_SETUP.md)
- [Validator Setup](VALIDATOR_SETUP.md)
- Appendix
  - [History of the Crypto Influence Insights Subnet](#history-of-the-crypto-influence-insights-subnet)

## Introduction

The **Crypto Influence Insights Subnet** is an innovative project aimed at uncovering cryptocurrency scams, analyzing networks of influencers promoting tokens, and offering insights into token-focused ecosystems. Built for advanced data analysis, it provides tools for scraping, analyzing, and visualizing token-centric data to empower users in detecting scams and assessing influence.

## Subnet Vision

The Crypto Influence Insights Subnet is designed to:

- **Detect Cryptocurrency Scams:** Analyze social media (e.g., Twitter) to identify networks and patterns of scam activities.
- **Assess Influencer Networks:** Provide metrics, rankings, and insights into the popularity and influence of individuals promoting tokens.
- **Empower Token-Centric Analysis:** Offer user-friendly tools like searches, graphs, metrics, and rankings to explore token ecosystems.
- **Enhance Security and Transparency:** Foster trust by improving visibility into potentially malicious activity in token ecosystems.

The subnet builds upon the legacy of blockchain data analysis while focusing on token-specific insights and detection of scam patterns.

## **Roadmap**

### **V1: Foundational Features**
- **V1.0: Basic Subnet Functionality (Completed):**
  - Scrape data for a single token.
  - Provide essential endpoints for token influencer analysis.
  - Deliver APIs for influencer metrics, graph generation, and influencer rankings.

- **V1.1: Twitter Presence (Completed):**
  - Introduce an endpoint and a Twitter bot to classify influencers by detecting anomalies.

- **V1.2: Snapshot Creation (Completed):**
  - Implement functionality for miners to create snapshots of token data.

---

### **V2: Immediate User-Facing Value**
- **V2.0: Receipt System for Subnet APIs (Completed):**
  - Develop a receipt mechanism for API usage to track work performed by miners, validators, and other subnet participants.
  - Ensure transparency and accountability for all API transactions.

- **V2.1: Implement Split and Merge Approach for Miner Data (Stage 1) (In Progress)**

- **V2.2: Add Time-Series Data Support (Stage 2)**

- **V2.3: Public Access APIs for Basic Insights:**
  - Enable end users to query basic information such as:
    - Influencer rankings for specific tokens.
    - Scam alerts based on basic heuristics.
  - Provide a free-tier API for public access to attract initial users.

- **V2.4: Real-Time Scam Alerts:**
  - Broadcast scam signals in near real-time via:
    - A Twitter bot.
    - Webhook subscriptions for developers and advanced users.

- **V2.5: Token Watchlist Feature:**
  - Allow users to monitor specific tokens and receive:
    - Alerts on influencer activity.
    - Notifications when a token’s risk score changes.

---

### **V3: Data and Infrastructure Enhancements**
- **V3.0: Monetization and Ecosystem Growth:**
  - **Freemium Access Model:**
    - Introduce tiered API access for free and paid users.
  - **Partnership with Token Platforms:**
    - Collaborate with launchpads and exchanges to provide:
      - Scam detection as a service.
      - Verified influencer metrics for token launches.

- **V3.1: Cross-Subnet Interoperability:**
  - **Integration with Other Subnets:**
    - Leverage data from complementary subnets to enhance scam detection.
  - **Enhanced Miner Collaboration Tools:**
    - Build miner dashboards for performance comparison and improvement tracking.

---

### **V4: Advanced Detection and Insights**
- **V4.0: Multi-Token Insights:**
  - Enable querying merged datasets for insights across multiple tokens.

- **V4.1: Expanded Advanced Detection Features:**
  - **Behavioral Scoring for Influencers:**
    - Analyze posting patterns, sentiment, and historical activity to detect suspicious behavior.
  - **Scam Campaign Profiling:**
    - Identify coordinated campaigns and flag for validator review.

---

### **V5: Visualization and Accessibility**
- **Visualization Dashboard:**
  - Create a user-friendly dashboard for API results visualization.

- **Jupyter Notebooks:**
  - Develop example notebooks for API and data usage, including reusable templates.

---

### **V6: LLM Integration**
- **LLM Capabilities for Detection:**
  - Add prompts for efficient influencer and scam detection with fuzzy thresholds.
- **Dedicated Detection Models:**
  - Train LLMs to improve detection of influencers and scams.

---

### **General Enhancements**
- **Open-Source Tools:**
  - Release lightweight tools and libraries to foster community adoption.

- **Regular Community Updates:**
  - Share progress, success stories, and roadmap updates via newsletters and Discord.

- **User Feedback Loops:**
  - Continuously improve APIs and tools based on community feedback.

---

## Overview

The Crypto Influence Insights Subnet is a token-focused platform leveraging blockchain and social media data to detect scams and assess influencer impact. Its key features include data scraping, graph analysis, metrics computation, and visualizations to provide actionable insights.

## Subnet Architecture Components

### **1. Subnet Owner**
   - **Role & Responsibilities:** The Subnet Owner acts as the coordinator, overseeing development, maintenance, and collaboration with miners and validators.

### **2. Validators**
   - **Role & Responsibilities:** Validators ensure data quality and accuracy. They host APIs and validate the work of miners.

### **3. Miners**
   - **Role & Responsibilities:** Miners scrape blockchain and social media data, focusing on token ecosystems. They detect patterns of influence and potential scams.

## Scoring

### Scoring Model

The **Validator** evaluates and ranks miners using a multi-layered scoring system based on performance and reliability. Scoring encourages integrity and efficiency within the subnet.

#### **Scoring Layers**
- **Layer 1: Response Evaluation**
   - No response: Score = `0`.

- **Layer 2: Component Evaluation in Challenges**
   - A single challenge is divided into multiple **components** (e.g., `tweet_id`, `user_id`, `follower_count`, etc.).
   - Failures in individual components are treated as **failed sub-challenges**:
     - **3 Failed Components:** Score = `0` (complete failure).
     - **2 Failed Components:** Score = `0.3`.
     - **1 Failed Component:** Score = `0.7`.
     - **No Failed Components:** Score = `1.0`.

- **Layer 3: Organic Prompt Rewards**
   - Rewards miners for the accuracy and real-world utility of their responses, providing bonuses for high follower counts (`>1000`).

- **Layer 4: Advanced Detection**
   - Scores miners on scam detection accuracy and pattern analysis (future enhancement).

### Final Score Calculation

The miner's final score incorporates:
- Base score from **failed sub-challenges**.
- Bonus for follower counts (`+0.1` for `follower_count > 1000`).
- Receipt multiplier to adjust scores dynamically.
- Maximum score capped at `1.0`.

## Challenges

### **Twitter Verification Challenge**

- **Objective:** Validate token-specific data, such as user influence and tweet metadata, for a given token (e.g., `"PEPE"`).

- **Process:**  
  - The validator sends **one challenge** with a token to analyze.  
  - The miner retrieves and verifies the following components:
    - `tweet_id`
    - `user_id`
    - `follower_count`
    - `tweet_date`
    - `verified` status.
  - Failures in any component are treated as **failed sub-challenges**.

- **Evaluation:**  
  - The validator assesses the accuracy of the miner's response for each component.  
  - Each failed component contributes to the miner's total failure count.

- **Impact:**  
  - Miners are scored based on their accuracy across all components.  
  - High accuracy improves scores and rewards, while frequent failures lead to penalties.

## Appendix

### History of the Crypto Influence Insights Subnet

**Formation and Launch**  
The Crypto Influence Insights Subnet was conceptualized in 2024 to address the growing prevalence of cryptocurrency scams. It focuses on token-specific data analysis and initially targets single-token data scraping.
