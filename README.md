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

## Roadmap

### V1
- **Basic Subnet Functionality:** Scraping data for a single token and providing essential endpoints for token influencers.
- **Key Deliverables:** APIs for influencer metrics, graphs, and rankings.

### V1.1
- **Adaptation and Polishing:** Refining endpoints based on real-world scenarios.

### V2
- **Multi-Token Insights:** Expanding subnet functionality to scrape data for multiple tokens and querying across tokens.
- **Scam Detection:** Introducing basic scam detection capabilities.

### V2.1
- **Visualization Dashboard:** Providing a dashboard for visualizing token insights and scam detection results.

### V3
- **Advanced Scam Detection:** Enhancing detection capabilities with advanced patterns and APIs.

### V4
- **Collaborative Validation:** Merging results from different miners and improving validation techniques.

### V5
- **Full-Scale API:** Offering a comprehensive scam and influencer detection API for real-time apps and agencies.

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
