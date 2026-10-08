window.LR_UNIVERSE_SOURCE_DATA = Object.freeze({
  sourceRepo:'lrgroup-bot/LR_Group',
  liveBase:'/lr-universe-api',
  service:{name:'LR Group shared operating platform',port:8788,localUrl:'http://127.0.0.1:8788',authority:'LR_GROUP',autonomousSpendInr:0},
  governance:{
    autonomousSpendInr:0,
    paidApiExecution:'blocked',
    humanApprovalRequired:['publishing','committing','merging','legal/accounting reliance','binding external actions'],
    ownerOnlyActions:['spend','purchase','payment','paid-subscription','paid-ad','bank-write','statutory-file','legal-sign','production-deploy','platform-connect','distribution-publish','distribution-schedule'],
    companyBoundary:'Operating-company system-of-record data stays in the company repository/service. LR Group receives minimum necessary events, aggregates, approvals and evidence references.'
  },
  company360Fields:['companyId','name','businessModel','customers','offerings','revenueDrivers','costDrivers','goals','processes','assets','suppliers','channels','competitors','marketContext','commercialProfile','marketSignalRefs','obligations','risks','metrics','evidence','updatedAt'],
  companyEvents:['company.health','sales.lead','sales.deal.changed','finance.summary','finance.receivable','compliance.alert','risk.signal','workforce.capacity','growth.opportunity','market.signal','competitor.signal','market.observation','market.decision','market.shift','customer.voice'],
  sharedDepartments:[
    {id:'lr-sales',name:'LR Sales',mission:'Grow revenue across connected LR companies.',capabilities:['lead-routing','pipeline-support','cross-sell','sales-intelligence']},
    {id:'lr-ca',name:'LR CA',mission:'Protect cash, accounting accuracy, tax readiness and group financial visibility.',capabilities:['accounting-support','gst-tax-prep','reconciliation','cashflow','consolidation-support']},
    {id:'lr-legal',name:'LR Legal',mission:'Provide legal research, contract support and escalation.',capabilities:['legal-research','contract-review','dispute-support']},
    {id:'lr-compliance',name:'LR Compliance',mission:'Keep licences, obligations, evidence and renewals under control.',capabilities:['licence-registry','obligation-tracking','evidence','renewals']},
    {id:'lr-hr',name:'LR HR',mission:'Manage human and AI workforce roles, learning, performance and capacity.',capabilities:['people','ai-workforce','roles','learning','performance']},
    {id:'lr-advertisement',name:'LR Advertisement',mission:'Acquire profitable demand and measure attributable return.',capabilities:['campaigns','creative','attribution','roi']},
    {id:'lr-procurement',name:'LR Procurement',mission:'Improve supplier quality, terms, resilience and total cost without autonomous purchasing.',capabilities:['vendor-intelligence','rfq','quote-comparison','vendor-risk','negotiation-drafts']},
    {id:'lr-strategy-growth',name:'LR Strategy & Growth',mission:'Find and prioritize evidence-backed profit and expansion opportunities.',capabilities:['opportunity-discovery','unit-economics','cross-company-growth','scenario-planning']},
    {id:'lr-intelligence',name:'LR Intelligence',mission:'Create exact, traceable group intelligence from connected company data.',capabilities:['kpi','semantic-metrics','forecast-inputs','anomaly-signals','management-briefs']},
    {id:'lr-audit-risk',name:'LR Audit & Risk',mission:'Independently test controls, risks, vendors, evidence and exceptions.',capabilities:['risk-register','controls','vendor-risk','audit-findings','evidence-chain']}
  ],
  ownerDesks:{
    WATCH:{mission:'See important external and internal changes early.',capabilities:['market-intelligence','competitors','customers','regulation','anomalies','opportunities']},
    GROW:{mission:'Increase profitable demand and business growth.',capabilities:['growth','campaigns','content','seo','distribution','experiments']},
    SELL:{mission:'Convert lawful demand into profitable customer outcomes.',capabilities:['leads','qualification','follow-up','proposal','cross-sell','customer-success']},
    OPERATE:{mission:'Run the companies accurately and efficiently.',capabilities:['cash','cost','procurement','compliance','legal','people','risk']},
    LEARN:{mission:'Turn verified outcomes into better future decisions.',capabilities:['decision-ledger','experiments','lessons','company-360','rishi-advisory']}
  },
  modules:['approval-learning','company-360','company-contract','daily-growth-council','decision-ledger','departments','distribution-engine','distribution-handoff','frontier-opportunity','governance','intelligence','knowledge','market-intelligence','market-store','mission-council','monetization-ledger','news-events','operations','opportunity-engine','owner-command-router','performance','platform-connections','platform-registry','process-intelligence','research-debate','rishi-advisory','risk','sales-followup','science-validation','security','treasury','workforce'],
  platforms:['YouTube','Facebook Page','Instagram','Blogger','LR Websites','Dailymotion','Rumble','LinkedIn','Substack','Pinterest','Snapchat'],
  providers:['Google Stitch','Pomelli','Google Flow Music','Google AI Studio','Google Antigravity','Google Opal','Google Flow','OpenDLSS-NR','Gemini Notebook','Mixboard'],
  divisionRoutes:['LR Group','LRS Motors','LR Mines & Minerals','LR Commerce','LR FinTech','LR Social Science','LR Sales','LR CA','LR Compliance','LR People','LR Operations','LR Technology','LR Production'],
  dailyGrowthCompanies:['lr-production','lr-commerce','lr-technology'],
  capabilities:{
    finance:['revenue','cost','grossContribution','receivables','cash','profitMargin','cashConversion','netLiquidity'],
    sales:['lead-journey','verified-price-stock-delivery-policy','follow-up-recommendation','human-escalation'],
    intelligence:['market-signals','competitor-signals','customer-voice','immutable-snapshots','decision-ledger','opportunity-ranking','company-360'],
    operations:['missions','workstreams','operations','bottlenecks','conformance','workforce-heartbeats'],
    risk:['risk-register','vendor-review','controls','evidence-chain'],
    research:['rishi-advisory','research-debate','science-validation','frontier-opportunity'],
    distribution:['approved-assets','rights/provenance checks','platform connections','release manifests','monetization ledger']
  },
  liveReadEndpoints:['/health','/api/providers','/api/distribution/platforms','/api/distribution/youtube/spec','/api/market-intelligence/schema']
});
