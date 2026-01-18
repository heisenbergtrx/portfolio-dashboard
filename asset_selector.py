"""
asset_selector.py - Varlık Seçim Modülü (v2)
============================================

Tam S&P 500 + NASDAQ 100 listesi ile varlık seçimi.

Yazar: Portfolio Dashboard
Tarih: Ocak 2026
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import streamlit as st
import yaml

logger = logging.getLogger(__name__)

# =============================================================================
# S&P 500 + NASDAQ 100 TAM LİSTE (Ocak 2026)
# =============================================================================

US_STOCKS_FULL = [
    # MEGA CAP TECH
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
    {"ticker": "GOOGL", "name": "Alphabet Inc. Class A", "sector": "Technology"},
    {"ticker": "GOOG", "name": "Alphabet Inc. Class C", "sector": "Technology"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer"},
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
    {"ticker": "META", "name": "Meta Platforms Inc.", "sector": "Technology"},
    {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Consumer"},
    {"ticker": "BRK.B", "name": "Berkshire Hathaway B", "sector": "Financial"},
    {"ticker": "TSM", "name": "Taiwan Semiconductor", "sector": "Technology"},
    
    # TECHNOLOGY
    {"ticker": "AVGO", "name": "Broadcom Inc.", "sector": "Technology"},
    {"ticker": "ORCL", "name": "Oracle Corporation", "sector": "Technology"},
    {"ticker": "AMD", "name": "Advanced Micro Devices", "sector": "Technology"},
    {"ticker": "CRM", "name": "Salesforce Inc.", "sector": "Technology"},
    {"ticker": "ADBE", "name": "Adobe Inc.", "sector": "Technology"},
    {"ticker": "CSCO", "name": "Cisco Systems Inc.", "sector": "Technology"},
    {"ticker": "ACN", "name": "Accenture plc", "sector": "Technology"},
    {"ticker": "INTC", "name": "Intel Corporation", "sector": "Technology"},
    {"ticker": "IBM", "name": "IBM Corporation", "sector": "Technology"},
    {"ticker": "QCOM", "name": "Qualcomm Inc.", "sector": "Technology"},
    {"ticker": "TXN", "name": "Texas Instruments", "sector": "Technology"},
    {"ticker": "INTU", "name": "Intuit Inc.", "sector": "Technology"},
    {"ticker": "AMAT", "name": "Applied Materials", "sector": "Technology"},
    {"ticker": "NOW", "name": "ServiceNow Inc.", "sector": "Technology"},
    {"ticker": "UBER", "name": "Uber Technologies", "sector": "Technology"},
    {"ticker": "SHOP", "name": "Shopify Inc.", "sector": "Technology"},
    {"ticker": "SQ", "name": "Block Inc. (Square)", "sector": "Technology"},
    {"ticker": "SNOW", "name": "Snowflake Inc.", "sector": "Technology"},
    {"ticker": "PLTR", "name": "Palantir Technologies", "sector": "Technology"},
    {"ticker": "NET", "name": "Cloudflare Inc.", "sector": "Technology"},
    {"ticker": "CRWD", "name": "CrowdStrike Holdings", "sector": "Technology"},
    {"ticker": "PANW", "name": "Palo Alto Networks", "sector": "Technology"},
    {"ticker": "DDOG", "name": "Datadog Inc.", "sector": "Technology"},
    {"ticker": "ZS", "name": "Zscaler Inc.", "sector": "Technology"},
    {"ticker": "MDB", "name": "MongoDB Inc.", "sector": "Technology"},
    {"ticker": "OKTA", "name": "Okta Inc.", "sector": "Technology"},
    {"ticker": "TWLO", "name": "Twilio Inc.", "sector": "Technology"},
    {"ticker": "HUBS", "name": "HubSpot Inc.", "sector": "Technology"},
    {"ticker": "ZM", "name": "Zoom Video Communications", "sector": "Technology"},
    {"ticker": "DOCU", "name": "DocuSign Inc.", "sector": "Technology"},
    {"ticker": "U", "name": "Unity Software Inc.", "sector": "Technology"},
    {"ticker": "PATH", "name": "UiPath Inc.", "sector": "Technology"},
    {"ticker": "TEAM", "name": "Atlassian Corporation", "sector": "Technology"},
    {"ticker": "WDAY", "name": "Workday Inc.", "sector": "Technology"},
    {"ticker": "VEEV", "name": "Veeva Systems Inc.", "sector": "Technology"},
    {"ticker": "SPLK", "name": "Splunk Inc.", "sector": "Technology"},
    {"ticker": "FTNT", "name": "Fortinet Inc.", "sector": "Technology"},
    {"ticker": "MRVL", "name": "Marvell Technology", "sector": "Technology"},
    {"ticker": "MU", "name": "Micron Technology", "sector": "Technology"},
    {"ticker": "LRCX", "name": "Lam Research Corp.", "sector": "Technology"},
    {"ticker": "KLAC", "name": "KLA Corporation", "sector": "Technology"},
    {"ticker": "SNPS", "name": "Synopsys Inc.", "sector": "Technology"},
    {"ticker": "CDNS", "name": "Cadence Design Systems", "sector": "Technology"},
    {"ticker": "ADSK", "name": "Autodesk Inc.", "sector": "Technology"},
    {"ticker": "ANSS", "name": "ANSYS Inc.", "sector": "Technology"},
    {"ticker": "HPE", "name": "Hewlett Packard Enterprise", "sector": "Technology"},
    {"ticker": "HPQ", "name": "HP Inc.", "sector": "Technology"},
    {"ticker": "DELL", "name": "Dell Technologies", "sector": "Technology"},
    {"ticker": "STX", "name": "Seagate Technology", "sector": "Technology"},
    {"ticker": "WDC", "name": "Western Digital Corp.", "sector": "Technology"},
    {"ticker": "ON", "name": "ON Semiconductor", "sector": "Technology"},
    {"ticker": "NXPI", "name": "NXP Semiconductors", "sector": "Technology"},
    {"ticker": "ADI", "name": "Analog Devices Inc.", "sector": "Technology"},
    {"ticker": "SWKS", "name": "Skyworks Solutions", "sector": "Technology"},
    {"ticker": "MPWR", "name": "Monolithic Power Systems", "sector": "Technology"},
    {"ticker": "ENPH", "name": "Enphase Energy Inc.", "sector": "Technology"},
    {"ticker": "SEDG", "name": "SolarEdge Technologies", "sector": "Technology"},
    
    # FINANCIAL
    {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financial"},
    {"ticker": "V", "name": "Visa Inc.", "sector": "Financial"},
    {"ticker": "MA", "name": "Mastercard Inc.", "sector": "Financial"},
    {"ticker": "BAC", "name": "Bank of America Corp.", "sector": "Financial"},
    {"ticker": "WFC", "name": "Wells Fargo & Co.", "sector": "Financial"},
    {"ticker": "GS", "name": "Goldman Sachs Group", "sector": "Financial"},
    {"ticker": "MS", "name": "Morgan Stanley", "sector": "Financial"},
    {"ticker": "SCHW", "name": "Charles Schwab Corp.", "sector": "Financial"},
    {"ticker": "C", "name": "Citigroup Inc.", "sector": "Financial"},
    {"ticker": "AXP", "name": "American Express Co.", "sector": "Financial"},
    {"ticker": "BLK", "name": "BlackRock Inc.", "sector": "Financial"},
    {"ticker": "SPGI", "name": "S&P Global Inc.", "sector": "Financial"},
    {"ticker": "CB", "name": "Chubb Limited", "sector": "Financial"},
    {"ticker": "MMC", "name": "Marsh & McLennan", "sector": "Financial"},
    {"ticker": "PGR", "name": "Progressive Corp.", "sector": "Financial"},
    {"ticker": "AON", "name": "Aon plc", "sector": "Financial"},
    {"ticker": "ICE", "name": "Intercontinental Exchange", "sector": "Financial"},
    {"ticker": "CME", "name": "CME Group Inc.", "sector": "Financial"},
    {"ticker": "MCO", "name": "Moody's Corporation", "sector": "Financial"},
    {"ticker": "USB", "name": "U.S. Bancorp", "sector": "Financial"},
    {"ticker": "PNC", "name": "PNC Financial Services", "sector": "Financial"},
    {"ticker": "TFC", "name": "Truist Financial Corp.", "sector": "Financial"},
    {"ticker": "COF", "name": "Capital One Financial", "sector": "Financial"},
    {"ticker": "AIG", "name": "American Intl Group", "sector": "Financial"},
    {"ticker": "MET", "name": "MetLife Inc.", "sector": "Financial"},
    {"ticker": "PRU", "name": "Prudential Financial", "sector": "Financial"},
    {"ticker": "ALL", "name": "Allstate Corp.", "sector": "Financial"},
    {"ticker": "TRV", "name": "Travelers Companies", "sector": "Financial"},
    {"ticker": "AFL", "name": "Aflac Inc.", "sector": "Financial"},
    {"ticker": "PYPL", "name": "PayPal Holdings Inc.", "sector": "Financial"},
    {"ticker": "COIN", "name": "Coinbase Global Inc.", "sector": "Financial"},
    {"ticker": "SOFI", "name": "SoFi Technologies", "sector": "Financial"},
    {"ticker": "HOOD", "name": "Robinhood Markets", "sector": "Financial"},
    {"ticker": "AFRM", "name": "Affirm Holdings", "sector": "Financial"},
    
    # HEALTHCARE
    {"ticker": "UNH", "name": "UnitedHealth Group", "sector": "Healthcare"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"},
    {"ticker": "LLY", "name": "Eli Lilly & Co.", "sector": "Healthcare"},
    {"ticker": "PFE", "name": "Pfizer Inc.", "sector": "Healthcare"},
    {"ticker": "ABBV", "name": "AbbVie Inc.", "sector": "Healthcare"},
    {"ticker": "MRK", "name": "Merck & Co. Inc.", "sector": "Healthcare"},
    {"ticker": "TMO", "name": "Thermo Fisher Scientific", "sector": "Healthcare"},
    {"ticker": "ABT", "name": "Abbott Laboratories", "sector": "Healthcare"},
    {"ticker": "DHR", "name": "Danaher Corporation", "sector": "Healthcare"},
    {"ticker": "BMY", "name": "Bristol-Myers Squibb", "sector": "Healthcare"},
    {"ticker": "AMGN", "name": "Amgen Inc.", "sector": "Healthcare"},
    {"ticker": "GILD", "name": "Gilead Sciences Inc.", "sector": "Healthcare"},
    {"ticker": "VRTX", "name": "Vertex Pharmaceuticals", "sector": "Healthcare"},
    {"ticker": "REGN", "name": "Regeneron Pharma", "sector": "Healthcare"},
    {"ticker": "ISRG", "name": "Intuitive Surgical", "sector": "Healthcare"},
    {"ticker": "MDT", "name": "Medtronic plc", "sector": "Healthcare"},
    {"ticker": "SYK", "name": "Stryker Corporation", "sector": "Healthcare"},
    {"ticker": "BSX", "name": "Boston Scientific", "sector": "Healthcare"},
    {"ticker": "ELV", "name": "Elevance Health Inc.", "sector": "Healthcare"},
    {"ticker": "CI", "name": "Cigna Group", "sector": "Healthcare"},
    {"ticker": "CVS", "name": "CVS Health Corp.", "sector": "Healthcare"},
    {"ticker": "HCA", "name": "HCA Healthcare Inc.", "sector": "Healthcare"},
    {"ticker": "MCK", "name": "McKesson Corporation", "sector": "Healthcare"},
    {"ticker": "ZTS", "name": "Zoetis Inc.", "sector": "Healthcare"},
    {"ticker": "BIIB", "name": "Biogen Inc.", "sector": "Healthcare"},
    {"ticker": "MRNA", "name": "Moderna Inc.", "sector": "Healthcare"},
    {"ticker": "ILMN", "name": "Illumina Inc.", "sector": "Healthcare"},
    {"ticker": "DXCM", "name": "DexCom Inc.", "sector": "Healthcare"},
    {"ticker": "IQV", "name": "IQVIA Holdings Inc.", "sector": "Healthcare"},
    {"ticker": "EW", "name": "Edwards Lifesciences", "sector": "Healthcare"},
    {"ticker": "A", "name": "Agilent Technologies", "sector": "Healthcare"},
    {"ticker": "BDX", "name": "Becton Dickinson & Co.", "sector": "Healthcare"},
    {"ticker": "IDXX", "name": "IDEXX Laboratories", "sector": "Healthcare"},
    {"ticker": "MTD", "name": "Mettler-Toledo Intl", "sector": "Healthcare"},
    {"ticker": "ALGN", "name": "Align Technology Inc.", "sector": "Healthcare"},
    
    # CONSUMER
    {"ticker": "WMT", "name": "Walmart Inc.", "sector": "Consumer"},
    {"ticker": "PG", "name": "Procter & Gamble Co.", "sector": "Consumer"},
    {"ticker": "KO", "name": "Coca-Cola Company", "sector": "Consumer"},
    {"ticker": "PEP", "name": "PepsiCo Inc.", "sector": "Consumer"},
    {"ticker": "COST", "name": "Costco Wholesale Corp.", "sector": "Consumer"},
    {"ticker": "HD", "name": "Home Depot Inc.", "sector": "Consumer"},
    {"ticker": "MCD", "name": "McDonald's Corp.", "sector": "Consumer"},
    {"ticker": "NKE", "name": "Nike Inc.", "sector": "Consumer"},
    {"ticker": "DIS", "name": "Walt Disney Company", "sector": "Consumer"},
    {"ticker": "NFLX", "name": "Netflix Inc.", "sector": "Consumer"},
    {"ticker": "SBUX", "name": "Starbucks Corp.", "sector": "Consumer"},
    {"ticker": "TGT", "name": "Target Corporation", "sector": "Consumer"},
    {"ticker": "LOW", "name": "Lowe's Companies Inc.", "sector": "Consumer"},
    {"ticker": "BKNG", "name": "Booking Holdings Inc.", "sector": "Consumer"},
    {"ticker": "ABNB", "name": "Airbnb Inc.", "sector": "Consumer"},
    {"ticker": "MAR", "name": "Marriott International", "sector": "Consumer"},
    {"ticker": "HLT", "name": "Hilton Worldwide", "sector": "Consumer"},
    {"ticker": "CMG", "name": "Chipotle Mexican Grill", "sector": "Consumer"},
    {"ticker": "YUM", "name": "Yum! Brands Inc.", "sector": "Consumer"},
    {"ticker": "ORLY", "name": "O'Reilly Automotive", "sector": "Consumer"},
    {"ticker": "AZO", "name": "AutoZone Inc.", "sector": "Consumer"},
    {"ticker": "ROST", "name": "Ross Stores Inc.", "sector": "Consumer"},
    {"ticker": "TJX", "name": "TJX Companies Inc.", "sector": "Consumer"},
    {"ticker": "DG", "name": "Dollar General Corp.", "sector": "Consumer"},
    {"ticker": "DLTR", "name": "Dollar Tree Inc.", "sector": "Consumer"},
    {"ticker": "EL", "name": "Estee Lauder Cos.", "sector": "Consumer"},
    {"ticker": "CL", "name": "Colgate-Palmolive Co.", "sector": "Consumer"},
    {"ticker": "KMB", "name": "Kimberly-Clark Corp.", "sector": "Consumer"},
    {"ticker": "MDLZ", "name": "Mondelez International", "sector": "Consumer"},
    {"ticker": "KHC", "name": "Kraft Heinz Company", "sector": "Consumer"},
    {"ticker": "GIS", "name": "General Mills Inc.", "sector": "Consumer"},
    {"ticker": "K", "name": "Kellogg Company", "sector": "Consumer"},
    {"ticker": "HSY", "name": "Hershey Company", "sector": "Consumer"},
    {"ticker": "MO", "name": "Altria Group Inc.", "sector": "Consumer"},
    {"ticker": "PM", "name": "Philip Morris Intl", "sector": "Consumer"},
    {"ticker": "STZ", "name": "Constellation Brands", "sector": "Consumer"},
    {"ticker": "DEO", "name": "Diageo plc", "sector": "Consumer"},
    {"ticker": "BUD", "name": "Anheuser-Busch InBev", "sector": "Consumer"},
    {"ticker": "LULU", "name": "Lululemon Athletica", "sector": "Consumer"},
    {"ticker": "GPS", "name": "Gap Inc.", "sector": "Consumer"},
    {"ticker": "ANF", "name": "Abercrombie & Fitch", "sector": "Consumer"},
    {"ticker": "DECK", "name": "Deckers Outdoor Corp.", "sector": "Consumer"},
    {"ticker": "CROX", "name": "Crocs Inc.", "sector": "Consumer"},
    {"ticker": "F", "name": "Ford Motor Company", "sector": "Consumer"},
    {"ticker": "GM", "name": "General Motors Co.", "sector": "Consumer"},
    {"ticker": "RIVN", "name": "Rivian Automotive", "sector": "Consumer"},
    {"ticker": "LCID", "name": "Lucid Group Inc.", "sector": "Consumer"},
    
    # INDUSTRIAL
    {"ticker": "CAT", "name": "Caterpillar Inc.", "sector": "Industrial"},
    {"ticker": "UNP", "name": "Union Pacific Corp.", "sector": "Industrial"},
    {"ticker": "HON", "name": "Honeywell International", "sector": "Industrial"},
    {"ticker": "UPS", "name": "United Parcel Service", "sector": "Industrial"},
    {"ticker": "BA", "name": "Boeing Company", "sector": "Industrial"},
    {"ticker": "RTX", "name": "RTX Corporation", "sector": "Industrial"},
    {"ticker": "LMT", "name": "Lockheed Martin Corp.", "sector": "Industrial"},
    {"ticker": "GE", "name": "General Electric Co.", "sector": "Industrial"},
    {"ticker": "DE", "name": "Deere & Company", "sector": "Industrial"},
    {"ticker": "MMM", "name": "3M Company", "sector": "Industrial"},
    {"ticker": "ETN", "name": "Eaton Corporation", "sector": "Industrial"},
    {"ticker": "ITW", "name": "Illinois Tool Works", "sector": "Industrial"},
    {"ticker": "EMR", "name": "Emerson Electric Co.", "sector": "Industrial"},
    {"ticker": "GD", "name": "General Dynamics Corp.", "sector": "Industrial"},
    {"ticker": "NOC", "name": "Northrop Grumman Corp.", "sector": "Industrial"},
    {"ticker": "FDX", "name": "FedEx Corporation", "sector": "Industrial"},
    {"ticker": "CSX", "name": "CSX Corporation", "sector": "Industrial"},
    {"ticker": "NSC", "name": "Norfolk Southern Corp.", "sector": "Industrial"},
    {"ticker": "WM", "name": "Waste Management Inc.", "sector": "Industrial"},
    {"ticker": "RSG", "name": "Republic Services Inc.", "sector": "Industrial"},
    {"ticker": "CARR", "name": "Carrier Global Corp.", "sector": "Industrial"},
    {"ticker": "OTIS", "name": "Otis Worldwide Corp.", "sector": "Industrial"},
    {"ticker": "JCI", "name": "Johnson Controls Intl", "sector": "Industrial"},
    {"ticker": "PH", "name": "Parker-Hannifin Corp.", "sector": "Industrial"},
    {"ticker": "ROK", "name": "Rockwell Automation", "sector": "Industrial"},
    {"ticker": "CMI", "name": "Cummins Inc.", "sector": "Industrial"},
    {"ticker": "PCAR", "name": "PACCAR Inc.", "sector": "Industrial"},
    {"ticker": "AME", "name": "AMETEK Inc.", "sector": "Industrial"},
    {"ticker": "FAST", "name": "Fastenal Company", "sector": "Industrial"},
    {"ticker": "VRSK", "name": "Verisk Analytics Inc.", "sector": "Industrial"},
    {"ticker": "CPRT", "name": "Copart Inc.", "sector": "Industrial"},
    {"ticker": "ODFL", "name": "Old Dominion Freight", "sector": "Industrial"},
    {"ticker": "URI", "name": "United Rentals Inc.", "sector": "Industrial"},
    
    # ENERGY
    {"ticker": "XOM", "name": "Exxon Mobil Corp.", "sector": "Energy"},
    {"ticker": "CVX", "name": "Chevron Corporation", "sector": "Energy"},
    {"ticker": "COP", "name": "ConocoPhillips", "sector": "Energy"},
    {"ticker": "SLB", "name": "Schlumberger Limited", "sector": "Energy"},
    {"ticker": "EOG", "name": "EOG Resources Inc.", "sector": "Energy"},
    {"ticker": "MPC", "name": "Marathon Petroleum", "sector": "Energy"},
    {"ticker": "PSX", "name": "Phillips 66", "sector": "Energy"},
    {"ticker": "VLO", "name": "Valero Energy Corp.", "sector": "Energy"},
    {"ticker": "PXD", "name": "Pioneer Natural Res.", "sector": "Energy"},
    {"ticker": "OXY", "name": "Occidental Petroleum", "sector": "Energy"},
    {"ticker": "HAL", "name": "Halliburton Company", "sector": "Energy"},
    {"ticker": "DVN", "name": "Devon Energy Corp.", "sector": "Energy"},
    {"ticker": "BKR", "name": "Baker Hughes Company", "sector": "Energy"},
    {"ticker": "FANG", "name": "Diamondback Energy", "sector": "Energy"},
    {"ticker": "KMI", "name": "Kinder Morgan Inc.", "sector": "Energy"},
    {"ticker": "WMB", "name": "Williams Companies", "sector": "Energy"},
    {"ticker": "OKE", "name": "ONEOK Inc.", "sector": "Energy"},
    {"ticker": "TRGP", "name": "Targa Resources Corp.", "sector": "Energy"},
    
    # UTILITIES & REAL ESTATE
    {"ticker": "NEE", "name": "NextEra Energy Inc.", "sector": "Utilities"},
    {"ticker": "DUK", "name": "Duke Energy Corp.", "sector": "Utilities"},
    {"ticker": "SO", "name": "Southern Company", "sector": "Utilities"},
    {"ticker": "D", "name": "Dominion Energy Inc.", "sector": "Utilities"},
    {"ticker": "AEP", "name": "American Electric Power", "sector": "Utilities"},
    {"ticker": "EXC", "name": "Exelon Corporation", "sector": "Utilities"},
    {"ticker": "SRE", "name": "Sempra Energy", "sector": "Utilities"},
    {"ticker": "XEL", "name": "Xcel Energy Inc.", "sector": "Utilities"},
    {"ticker": "PEG", "name": "Public Service Enterprise", "sector": "Utilities"},
    {"ticker": "ED", "name": "Consolidated Edison", "sector": "Utilities"},
    {"ticker": "WEC", "name": "WEC Energy Group", "sector": "Utilities"},
    {"ticker": "ES", "name": "Eversource Energy", "sector": "Utilities"},
    {"ticker": "AWK", "name": "American Water Works", "sector": "Utilities"},
    {"ticker": "AMT", "name": "American Tower Corp.", "sector": "Real Estate"},
    {"ticker": "PLD", "name": "Prologis Inc.", "sector": "Real Estate"},
    {"ticker": "CCI", "name": "Crown Castle Inc.", "sector": "Real Estate"},
    {"ticker": "EQIX", "name": "Equinix Inc.", "sector": "Real Estate"},
    {"ticker": "PSA", "name": "Public Storage", "sector": "Real Estate"},
    {"ticker": "SPG", "name": "Simon Property Group", "sector": "Real Estate"},
    {"ticker": "WELL", "name": "Welltower Inc.", "sector": "Real Estate"},
    {"ticker": "DLR", "name": "Digital Realty Trust", "sector": "Real Estate"},
    {"ticker": "O", "name": "Realty Income Corp.", "sector": "Real Estate"},
    {"ticker": "VICI", "name": "VICI Properties Inc.", "sector": "Real Estate"},
    {"ticker": "AVB", "name": "AvalonBay Communities", "sector": "Real Estate"},
    {"ticker": "EQR", "name": "Equity Residential", "sector": "Real Estate"},
    
    # MATERIALS
    {"ticker": "LIN", "name": "Linde plc", "sector": "Materials"},
    {"ticker": "APD", "name": "Air Products & Chemicals", "sector": "Materials"},
    {"ticker": "SHW", "name": "Sherwin-Williams Co.", "sector": "Materials"},
    {"ticker": "ECL", "name": "Ecolab Inc.", "sector": "Materials"},
    {"ticker": "FCX", "name": "Freeport-McMoRan Inc.", "sector": "Materials"},
    {"ticker": "NEM", "name": "Newmont Corporation", "sector": "Materials"},
    {"ticker": "NUE", "name": "Nucor Corporation", "sector": "Materials"},
    {"ticker": "DOW", "name": "Dow Inc.", "sector": "Materials"},
    {"ticker": "DD", "name": "DuPont de Nemours", "sector": "Materials"},
    {"ticker": "PPG", "name": "PPG Industries Inc.", "sector": "Materials"},
    {"ticker": "VMC", "name": "Vulcan Materials Co.", "sector": "Materials"},
    {"ticker": "MLM", "name": "Martin Marietta Materials", "sector": "Materials"},
    {"ticker": "CTVA", "name": "Corteva Inc.", "sector": "Materials"},
    {"ticker": "ALB", "name": "Albemarle Corporation", "sector": "Materials"},
    {"ticker": "IFF", "name": "Intl Flavors & Fragrances", "sector": "Materials"},
    
    # COMMUNICATION
    {"ticker": "T", "name": "AT&T Inc.", "sector": "Communication"},
    {"ticker": "VZ", "name": "Verizon Communications", "sector": "Communication"},
    {"ticker": "TMUS", "name": "T-Mobile US Inc.", "sector": "Communication"},
    {"ticker": "CMCSA", "name": "Comcast Corporation", "sector": "Communication"},
    {"ticker": "CHTR", "name": "Charter Communications", "sector": "Communication"},
    {"ticker": "WBD", "name": "Warner Bros. Discovery", "sector": "Communication"},
    {"ticker": "PARA", "name": "Paramount Global", "sector": "Communication"},
    {"ticker": "EA", "name": "Electronic Arts Inc.", "sector": "Communication"},
    {"ticker": "TTWO", "name": "Take-Two Interactive", "sector": "Communication"},
    {"ticker": "RBLX", "name": "Roblox Corporation", "sector": "Communication"},
    {"ticker": "MTCH", "name": "Match Group Inc.", "sector": "Communication"},
    {"ticker": "SNAP", "name": "Snap Inc.", "sector": "Communication"},
    {"ticker": "PINS", "name": "Pinterest Inc.", "sector": "Communication"},
    {"ticker": "SPOT", "name": "Spotify Technology", "sector": "Communication"},
    
    # INTERNATIONAL / ADR
    {"ticker": "BABA", "name": "Alibaba Group (ADR)", "sector": "International"},
    {"ticker": "JD", "name": "JD.com Inc. (ADR)", "sector": "International"},
    {"ticker": "PDD", "name": "PDD Holdings (ADR)", "sector": "International"},
    {"ticker": "BIDU", "name": "Baidu Inc. (ADR)", "sector": "International"},
    {"ticker": "NIO", "name": "NIO Inc. (ADR)", "sector": "International"},
    {"ticker": "XPEV", "name": "XPeng Inc. (ADR)", "sector": "International"},
    {"ticker": "LI", "name": "Li Auto Inc. (ADR)", "sector": "International"},
    {"ticker": "SE", "name": "Sea Limited (ADR)", "sector": "International"},
    {"ticker": "GRAB", "name": "Grab Holdings (ADR)", "sector": "International"},
    {"ticker": "MELI", "name": "MercadoLibre Inc.", "sector": "International"},
    {"ticker": "NU", "name": "Nu Holdings Ltd.", "sector": "International"},
    {"ticker": "SONY", "name": "Sony Group Corp. (ADR)", "sector": "International"},
    {"ticker": "TM", "name": "Toyota Motor (ADR)", "sector": "International"},
    {"ticker": "HMC", "name": "Honda Motor (ADR)", "sector": "International"},
    {"ticker": "ASML", "name": "ASML Holding (ADR)", "sector": "International"},
    {"ticker": "SAP", "name": "SAP SE (ADR)", "sector": "International"},
    {"ticker": "UL", "name": "Unilever plc (ADR)", "sector": "International"},
    {"ticker": "NVS", "name": "Novartis AG (ADR)", "sector": "International"},
    {"ticker": "AZN", "name": "AstraZeneca plc (ADR)", "sector": "International"},
    {"ticker": "GSK", "name": "GSK plc (ADR)", "sector": "International"},
    {"ticker": "SNY", "name": "Sanofi (ADR)", "sector": "International"},
    {"ticker": "SHEL", "name": "Shell plc (ADR)", "sector": "International"},
    {"ticker": "BP", "name": "BP plc (ADR)", "sector": "International"},
    {"ticker": "TTE", "name": "TotalEnergies (ADR)", "sector": "International"},
]

# Popüler kripto listesi
POPULAR_CRYPTOS = [
    {"symbol": "BTC/USDT", "name": "Bitcoin"},
    {"symbol": "ETH/USDT", "name": "Ethereum"},
    {"symbol": "SOL/USDT", "name": "Solana"},
    {"symbol": "BNB/USDT", "name": "Binance Coin"},
    {"symbol": "XRP/USDT", "name": "Ripple"},
    {"symbol": "ADA/USDT", "name": "Cardano"},
    {"symbol": "AVAX/USDT", "name": "Avalanche"},
    {"symbol": "DOGE/USDT", "name": "Dogecoin"},
    {"symbol": "DOT/USDT", "name": "Polkadot"},
    {"symbol": "MATIC/USDT", "name": "Polygon"},
    {"symbol": "LINK/USDT", "name": "Chainlink"},
    {"symbol": "UNI/USDT", "name": "Uniswap"},
    {"symbol": "ATOM/USDT", "name": "Cosmos"},
    {"symbol": "LTC/USDT", "name": "Litecoin"},
    {"symbol": "APT/USDT", "name": "Aptos"},
    {"symbol": "ARB/USDT", "name": "Arbitrum"},
    {"symbol": "OP/USDT", "name": "Optimism"},
    {"symbol": "NEAR/USDT", "name": "NEAR Protocol"},
    {"symbol": "FIL/USDT", "name": "Filecoin"},
    {"symbol": "INJ/USDT", "name": "Injective"},
    {"symbol": "SUI/USDT", "name": "Sui"},
    {"symbol": "SEI/USDT", "name": "Sei"},
    {"symbol": "TIA/USDT", "name": "Celestia"},
    {"symbol": "RENDER/USDT", "name": "Render"},
    {"symbol": "FET/USDT", "name": "Fetch.ai"},
    {"symbol": "RNDR/USDT", "name": "Render Token"},
    {"symbol": "GRT/USDT", "name": "The Graph"},
    {"symbol": "IMX/USDT", "name": "Immutable X"},
    {"symbol": "STX/USDT", "name": "Stacks"},
    {"symbol": "AAVE/USDT", "name": "Aave"},
]

# Popüler TEFAS fonları
POPULAR_TEFAS = [
    {"code": "DLY", "name": "Deniz Portföy Para Piyasası Fonu"},
    {"code": "DIP", "name": "Deniz Portföy Kısa Vadeli Borçlanma Araçları"},
    {"code": "MET", "name": "İş Portföy BIST 30 Endeks HSY Fonu"},
    {"code": "AKF", "name": "Ak Portföy Kısa Vadeli Borçlanma Araçları"},
    {"code": "YAF", "name": "Yapı Kredi Portföy Altın Fonu"},
    {"code": "GAF", "name": "Garanti Portföy Altın Fonu"},
    {"code": "TI2", "name": "TEB Portföy İkinci Değişken Fon"},
    {"code": "IPB", "name": "İş Portföy BIST Banka Endeksi HSY Fonu"},
    {"code": "YEF", "name": "Yapı Kredi Portföy Yab. Tek. Sek. HSY Fonu"},
    {"code": "AFT", "name": "Ak Portföy Amerikan Teknoloji Yab. HSY Fonu"},
    {"code": "ZPX", "name": "Ziraat Portföy S&P 500 Yab. HSY Fonu"},
    {"code": "MAC", "name": "Marmara Capital Portföy Değişken Fonu"},
    {"code": "TPE", "name": "Tacirler Portföy Hisse Senedi Fonu"},
    {"code": "GZO", "name": "Garanti Portföy Birinci Değişken Fon"},
]


def load_config(config_path: str = "config.yaml") -> dict:
    """Config dosyasını yükle."""
    config_file = Path(config_path)
    
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    return {
        "settings": {"risk_free_rate": 0.35, "cache_ttl_seconds": 3600},
        "thresholds": {"weekly_loss_threshold": -4.0, "weekly_gain_threshold": 7.0, "weight_deviation_threshold": 5.0},
        "tefas_funds": [],
        "us_stocks": [],
        "crypto": []
    }


def save_config(config: dict, config_path: str = "config.yaml") -> bool:
    """Config dosyasını kaydet."""
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return True
    except Exception as e:
        logger.error(f"Config kaydetme hatası: {e}")
        return False


def render_asset_selector():
    """Varlık seçim sayfasını render et."""
    
    st.markdown("## 📦 Portföy Yönetimi")
    st.markdown("Portföyünüze varlık ekleyin, düzenleyin veya kaldırın.")
    
    if 'portfolio_config' not in st.session_state:
        st.session_state.portfolio_config = load_config()
    
    config = st.session_state.portfolio_config
    
    tab1, tab2, tab3, tab4 = st.tabs(["🇺🇸 ABD Hisseleri", "₿ Kripto", "🇹🇷 TEFAS", "💾 Kaydet"])
    
    # =========================================================================
    # TAB 1: ABD HİSSELERİ
    # =========================================================================
    with tab1:
        st.markdown("### ABD Hisse Senetleri")
        st.caption(f"📊 Toplam {len(US_STOCKS_FULL)} hisse mevcut (S&P 500 + NASDAQ 100)")
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            # Arama ve filtreleme
            search_query = st.text_input(
                "🔍 Hisse Ara (ticker veya şirket adı)",
                placeholder="Örn: AMD, Apple, Tesla...",
                key="us_stock_search"
            )
            
            # Sektör filtresi
            sectors = sorted(set(s['sector'] for s in US_STOCKS_FULL))
            selected_sector = st.selectbox(
                "📁 Sektör Filtrele",
                options=["Tümü"] + sectors,
                key="sector_filter"
            )
            
            # Filtreleme
            filtered_stocks = US_STOCKS_FULL.copy()
            
            if search_query:
                search_lower = search_query.lower()
                filtered_stocks = [
                    s for s in filtered_stocks 
                    if search_lower in s['ticker'].lower() or search_lower in s['name'].lower()
                ]
            
            if selected_sector != "Tümü":
                filtered_stocks = [s for s in filtered_stocks if s['sector'] == selected_sector]
            
            # Sonuçları göster
            st.markdown(f"**Sonuçlar: {len(filtered_stocks)} hisse**")
            
            existing_tickers = [s['ticker'] for s in config.get('us_stocks', [])]
            
            # Grid görünümü
            for i in range(0, min(len(filtered_stocks), 30), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    idx = i + j
                    if idx < len(filtered_stocks):
                        stock = filtered_stocks[idx]
                        disabled = stock['ticker'] in existing_tickers
                        
                        with col:
                            btn_label = f"{'✓ ' if disabled else ''}{stock['ticker']}"
                            if st.button(
                                btn_label,
                                key=f"add_us_{stock['ticker']}_{idx}",
                                disabled=disabled,
                                help=f"{stock['name']} ({stock['sector']})",
                                use_container_width=True
                            ):
                                if 'us_stocks' not in config:
                                    config['us_stocks'] = []
                                config['us_stocks'].append({
                                    'ticker': stock['ticker'],
                                    'shares': 1.0,
                                    'target_weight': 5.0
                                })
                                st.rerun()
            
            if len(filtered_stocks) > 30:
                st.info(f"...ve {len(filtered_stocks) - 30} hisse daha. Aramayı daraltın.")
        
        with col2:
            st.markdown("### 📋 Seçili Hisseler")
            
            if config.get('us_stocks'):
                for idx, stock in enumerate(config['us_stocks']):
                    with st.container():
                        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                        
                        with c1:
                            st.markdown(f"**{stock['ticker']}**")
                        
                        with c2:
                            new_shares = st.number_input(
                                "Adet", min_value=0.0, value=float(stock.get('shares', 1)),
                                step=1.0, key=f"sh_us_{idx}", label_visibility="collapsed"
                            )
                            config['us_stocks'][idx]['shares'] = new_shares
                        
                        with c3:
                            new_weight = st.number_input(
                                "%", min_value=0.0, max_value=100.0,
                                value=float(stock.get('target_weight', 5)),
                                step=1.0, key=f"wt_us_{idx}", label_visibility="collapsed"
                            )
                            config['us_stocks'][idx]['target_weight'] = new_weight
                        
                        with c4:
                            if st.button("🗑️", key=f"del_us_{idx}"):
                                config['us_stocks'].pop(idx)
                                st.rerun()
            else:
                st.info("Henüz hisse eklenmedi.")
    
    # =========================================================================
    # TAB 2: KRİPTO
    # =========================================================================
    with tab2:
        st.markdown("### Kripto Paralar")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Popüler Kripto Paralar:**")
            
            existing_cryptos = [c['symbol'] for c in config.get('crypto', [])]
            
            for i in range(0, len(POPULAR_CRYPTOS), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    idx = i + j
                    if idx < len(POPULAR_CRYPTOS):
                        crypto = POPULAR_CRYPTOS[idx]
                        disabled = crypto['symbol'] in existing_cryptos
                        
                        with col:
                            if st.button(
                                f"{'✓ ' if disabled else ''}{crypto['name'][:10]}",
                                key=f"add_crypto_{idx}",
                                disabled=disabled,
                                help=crypto['symbol'],
                                use_container_width=True
                            ):
                                if 'crypto' not in config:
                                    config['crypto'] = []
                                config['crypto'].append({
                                    'symbol': crypto['symbol'],
                                    'amount': 0.01,
                                    'target_weight': 5.0
                                })
                                st.rerun()
            
            st.markdown("---")
            st.markdown("**Manuel Ekle:**")
            custom_crypto = st.text_input("Sembol (örn: BTC/USDT)", key="custom_crypto")
            if st.button("Ekle", key="add_custom_crypto"):
                if custom_crypto and "/" in custom_crypto:
                    if custom_crypto.upper() not in existing_cryptos:
                        if 'crypto' not in config:
                            config['crypto'] = []
                        config['crypto'].append({
                            'symbol': custom_crypto.upper(),
                            'amount': 0.01,
                            'target_weight': 5.0
                        })
                        st.rerun()
        
        with col2:
            st.markdown("### 📋 Seçili Kripto")
            
            if config.get('crypto'):
                for idx, crypto in enumerate(config['crypto']):
                    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                    
                    with c1:
                        st.markdown(f"**{crypto['symbol'].split('/')[0]}**")
                    
                    with c2:
                        new_amount = st.number_input(
                            "Miktar", min_value=0.0, value=float(crypto.get('amount', 0.01)),
                            step=0.01, format="%.4f", key=f"am_cr_{idx}", label_visibility="collapsed"
                        )
                        config['crypto'][idx]['amount'] = new_amount
                    
                    with c3:
                        new_weight = st.number_input(
                            "%", min_value=0.0, max_value=100.0,
                            value=float(crypto.get('target_weight', 5)),
                            step=1.0, key=f"wt_cr_{idx}", label_visibility="collapsed"
                        )
                        config['crypto'][idx]['target_weight'] = new_weight
                    
                    with c4:
                        if st.button("🗑️", key=f"del_cr_{idx}"):
                            config['crypto'].pop(idx)
                            st.rerun()
            else:
                st.info("Henüz kripto eklenmedi.")
    
    # =========================================================================
    # TAB 3: TEFAS
    # =========================================================================
    with tab3:
        st.markdown("### TEFAS Yatırım Fonları")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Popüler Fonlar:**")
            
            existing_tefas = [f['code'] for f in config.get('tefas_funds', [])]
            
            for fund in POPULAR_TEFAS:
                disabled = fund['code'] in existing_tefas
                c1, c2 = st.columns([1, 4])
                
                with c1:
                    if st.button(
                        f"{'✓ ' if disabled else ''}{fund['code']}",
                        key=f"add_tefas_{fund['code']}",
                        disabled=disabled
                    ):
                        if 'tefas_funds' not in config:
                            config['tefas_funds'] = []
                        config['tefas_funds'].append({
                            'code': fund['code'],
                            'shares': 100.0,
                            'target_weight': 5.0
                        })
                        st.rerun()
                
                with c2:
                    st.caption(fund['name'][:40])
            
            st.markdown("---")
            st.markdown("**Manuel Ekle:**")
            custom_tefas = st.text_input("Fon Kodu", key="custom_tefas", max_chars=5)
            if st.button("Ekle", key="add_custom_tefas"):
                if custom_tefas and len(custom_tefas) >= 2:
                    if custom_tefas.upper() not in existing_tefas:
                        if 'tefas_funds' not in config:
                            config['tefas_funds'] = []
                        config['tefas_funds'].append({
                            'code': custom_tefas.upper(),
                            'shares': 100.0,
                            'target_weight': 5.0
                        })
                        st.rerun()
        
        with col2:
            st.markdown("### 📋 Seçili Fonlar")
            
            if config.get('tefas_funds'):
                for idx, fund in enumerate(config['tefas_funds']):
                    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                    
                    with c1:
                        st.markdown(f"**{fund['code']}**")
                    
                    with c2:
                        new_shares = st.number_input(
                            "Pay", min_value=0.0, value=float(fund.get('shares', 100)),
                            step=100.0, key=f"sh_tf_{idx}", label_visibility="collapsed"
                        )
                        config['tefas_funds'][idx]['shares'] = new_shares
                    
                    with c3:
                        new_weight = st.number_input(
                            "%", min_value=0.0, max_value=100.0,
                            value=float(fund.get('target_weight', 5)),
                            step=1.0, key=f"wt_tf_{idx}", label_visibility="collapsed"
                        )
                        config['tefas_funds'][idx]['target_weight'] = new_weight
                    
                    with c4:
                        if st.button("🗑️", key=f"del_tf_{idx}"):
                            config['tefas_funds'].pop(idx)
                            st.rerun()
            else:
                st.info("Henüz fon eklenmedi.")
    
    # =========================================================================
    # TAB 4: KAYDET
    # =========================================================================
    with tab4:
        st.markdown("### 💾 Portföy Özeti")
        
        # Özet
        total_weight = 0.0
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            us_count = len(config.get('us_stocks', []))
            us_weight = sum(s.get('target_weight', 0) for s in config.get('us_stocks', []))
            st.metric("🇺🇸 ABD Hisseleri", f"{us_count} adet", f"%{us_weight:.0f}")
            total_weight += us_weight
        
        with c2:
            crypto_count = len(config.get('crypto', []))
            crypto_weight = sum(c.get('target_weight', 0) for c in config.get('crypto', []))
            st.metric("₿ Kripto", f"{crypto_count} adet", f"%{crypto_weight:.0f}")
            total_weight += crypto_weight
        
        with c3:
            tefas_count = len(config.get('tefas_funds', []))
            tefas_weight = sum(f.get('target_weight', 0) for f in config.get('tefas_funds', []))
            st.metric("🇹🇷 TEFAS", f"{tefas_count} adet", f"%{tefas_weight:.0f}")
            total_weight += tefas_weight
        
        st.markdown("---")
        
        if total_weight == 100:
            st.success(f"✅ Toplam ağırlık: %{total_weight:.0f}")
        elif total_weight < 100:
            st.warning(f"⚠️ Toplam: %{total_weight:.0f} (Eksik: %{100 - total_weight:.0f})")
        else:
            st.error(f"❌ Toplam: %{total_weight:.0f} (Fazla: %{total_weight - 100:.0f})")
        
        st.markdown("---")
        
        if st.button("💾 Config Kaydet", type="primary", use_container_width=True):
            if save_config(config):
                st.success("✅ Kaydedildi!")
                st.balloons()
                st.session_state.portfolio_config = config
                st.session_state.config = None
            else:
                st.error("❌ Hata!")
        
        with st.expander("📄 Config Önizleme"):
            st.code(yaml.dump(config, default_flow_style=False, allow_unicode=True), language="yaml")


if __name__ == "__main__":
    st.set_page_config(page_title="Varlık Seçici", layout="wide")
    render_asset_selector()
