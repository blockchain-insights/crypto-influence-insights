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

# **Roadmap**

## **V1**
- **Basic Subnet Functionality**: Develop the ability to scrape data for a single token and provide essential endpoints for token influencer analysis.
- **Key Deliverables**: APIs for influencer metrics, graph generation, and influencer rankings.

## **V1.1**
- **Twitter Presence**: Introduce a new endpoint and build a Twitter bot to classify influencers by detecting anomalies.

## **V2**
- **Snapshot Creation**: Implement an endpoint and the underlying functionality for creating miner database snapshots (Proof of Concept).
- **Data Merging Across Miners**: Develop an approach to merge datasets from multiple miners over time, including new endpoints, functionality, and supporting infrastructure (DevOps).
- **Multi-Token Insights**: Expand subnet functionality to query merged datasets for insights across multiple tokens.

## **V3**
- **Advanced Influencer Detection**: Enhance influencer detection capabilities with new APIs and algorithms (e.g., PageRank, Leiden, Louvain, vector search).
- **Advanced Scam Detection**: Develop advanced APIs and algorithms for scam detection (e.g., PageRank, Leiden, Louvain, vector search).

> *Note*: Both **Advanced Influencer Detection** and **Advanced Scam Detection** will focus on identifying coordinated campaigns, including promoting or anti-promoting tokens, detecting scam groups, and exposing associated accounts.

## **V4**
- **Visualization Dashboard**: Create a user-friendly dashboard to visualize results from the APIs.
- **Jupyter Notebooks**: Develop Jupyter notebooks with examples of API and data usage, including graphs and reusable code templates, and host a repository with essential templates.

## **V5**
- **Adding LLM Capabilities to Influencer/Scam Detection**: Introduce prompts to detect various classes of influencers and scams more efficiently, with fuzzy thresholds and support for complex patterns.
- **Dedicated Models for Influencer/Scam Detection**: Train dedicated LLM models (at the miner level) for improved detection of influencers and scams.


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
