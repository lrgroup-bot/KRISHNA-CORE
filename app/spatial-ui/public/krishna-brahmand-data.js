window.KRISHNA_BRAHMAND_DATA = {
  root: ['rishi-council','sudarshan','research','vision','protection'],
  nodes: {
    krishna:{label:'KRISHNA',icon:'ॐ',role:'Authority · conversation · orchestration',endpoint:'/api/status',aliases:['krishna']},
    'rishi-council':{label:'RISHI COUNCIL',icon:'△',role:'Specialist reasoning council',endpoint:'/api/brahma/status',aliases:['rishi','council','brahma'],children:['vashistha','vishwamitra','vyasa','sushruta','kashyapa','atri','gautama','jamadagni','bharadvaja','kanada','kapila','patanjali','yajnavalkya','agastya']},
    sudarshan:{label:'SUDARSHAN',icon:'☸',role:'Execution · testing · verification',endpoint:'/api/tasks?project=KRISHNA&limit=300',aliases:['sudarshan'],children:['vishwakarma','ui-guardian','narad','project-perfection','developer','specialists']},
    research:{label:'KNOWLEDGE & RESEARCH',icon:'✦',role:'Deep research · verified knowledge · browser evidence',endpoint:'/api/brahma/intelligence/status',aliases:['brahmagyan','research','gyan'],children:['brahma','brahmagyan','gyan-bhandar','garuda','garudanetra']},
    vision:{label:'VISION & LEARNING',icon:'◉',role:'Vision · camera · screen/audio learning',aliases:['hawkeye','surya','chandra','vision'],children:['hawkeye','suryadev','chandradev']},
    protection:{label:'PROTECTION & RECOVERY',icon:'⬡',role:'Security · privacy · recovery',endpoint:'/api/kabach/privacy/status',aliases:['kabach','mrityunjaya','security'],children:['kabach','mrityunjaya']},
    brahma:{label:'BRAHMA',icon:'◈',role:'Knowledge process · council coordination',endpoint:'/api/brahma/status',aliases:['brahma']},
    brahmagyan:{label:'BRAHMAGYAN',icon:'✦',role:'Deep research · synthesis',aliases:['brahmagyan']},
    'gyan-bhandar':{label:'GYAN-BHANDAR',icon:'▤',role:'Verified knowledge archive',endpoint:'/api/gyan-bhandar/archive/status',aliases:['gyan-bhandar','gyan bhandar']},
    garuda:{label:'GARUDA',icon:'◆',role:'Research scout · evidence',aliases:['garuda']},
    garudanetra:{label:'GARUDANETRA',icon:'◉',role:'Browser · web research · evidence',endpoint:'/api/garudanetra/fabric',aliases:['garudanetra']},
    hawkeye:{label:'HAWKEYE',icon:'◉',role:'Vision · mobile · field sensing',endpoint:'/api/hawkeye/ruview/status',aliases:['hawkeye']},
    suryadev:{label:'SURYA DEV',icon:'☀',role:'Screen/audio learning',aliases:['suryadev','surya dev','surya']},
    chandradev:{label:'CHANDRA DEV',icon:'◐',role:'Camera observation',aliases:['chandradev','chandra dev','chandra']},
    kabach:{label:'KABACH',icon:'⬡',role:'Security · privacy · project boundary',endpoint:'/api/kabach/privacy/status',aliases:['kabach']},
    mrityunjaya:{label:'MRITYUNJAYA',icon:'♜',role:'Diagnosis · recovery · self-heal',endpoint:'/api/mrityunjay/status',aliases:['mrityunjaya','mrityunjay']},
    vishwakarma:{label:'VISHWAKARMA',icon:'⚒',role:'Engineering · repair · design verification',endpoint:'/api/design/status',aliases:['vishwakarma']},
    'ui-guardian':{label:'UI GUARDIAN',icon:'◇',role:'Rendered UI verification',endpoint:'/api/ui-guardian/registry?project=KRISHNA',aliases:['ui guardian','ui-guardian']},
    narad:{label:'NARAD',icon:'♫',role:'Messaging · workflows · automation',aliases:['narad']},
    'project-perfection':{label:'PROJECT PERFECTION',icon:'◎',role:'Quality gates · project perfection',endpoint:'/api/project-perfection/status',aliases:['project perfection','project-perfection']},
    developer:{label:'DEVELOPER',icon:'⌘',role:'Code implementation worker',aliases:['developer']},
    specialists:{label:'SPECIALISTS',icon:'⌘',role:'Specialist execution pool',aliases:['specialist','specialists']},
    vashistha:{label:'VASHISTHA',icon:'✧',role:'Council reasoning',aliases:['vashistha']},
    vishwamitra:{label:'VISHWAMITRA',icon:'✧',role:'Council reasoning',aliases:['vishwamitra']},
    vyasa:{label:'VYASA',icon:'✧',role:'Synthesis · knowledge',aliases:['vyasa']},
    sushruta:{label:'SUSHRUTA',icon:'✧',role:'Health/medical specialist knowledge',aliases:['sushruta']},
    kashyapa:{label:'KASHYAPA',icon:'✧',role:'Council specialist',aliases:['kashyapa']},
    atri:{label:'ATRI',icon:'✧',role:'Council specialist',aliases:['atri']},
    gautama:{label:'GAUTAMA',icon:'✧',role:'Logic · reasoning',aliases:['gautama']},
    jamadagni:{label:'JAMADAGNI',icon:'✧',role:'Council specialist',aliases:['jamadagni']},
    bharadvaja:{label:'BHARADVAJA',icon:'✧',role:'Engineering/science knowledge',aliases:['bharadvaja']},
    canada_placeholder:null,
    kanada:{label:'KANADA',icon:'✧',role:'Physics · analytical reasoning',aliases:['kanada']},
    kapila:{label:'KAPILA',icon:'✧',role:'Systems reasoning',aliases:['kapila']},
    patanjali:{label:'PATANJALI',icon:'✧',role:'Mind · discipline · wellness knowledge',aliases:['patanjali']},
    yajnavalkya:{label:'YAJNAVALKYA',icon:'✧',role:'Philosophy · reasoning',aliases:['yajnavalkya']},
    agastya:{label:'AGASTYA',icon:'✧',role:'Applied knowledge · engineering',aliases:['agastya']}
  },
  input: {
    'rishi-council':['KRISHNA'],sudarshan:['KRISHNA'],research:['KRISHNA'],vision:['KRISHNA'],protection:['KRISHNA'],
    brahma:['RISHI COUNCIL','KRISHNA'],brahmagyan:['BRAHMA','KRISHNA'],'gyan-bhandar':['BRAHMA','BRAHMAGYAN'],garuda:['KRISHNA'],garudanetra:['GARUDA','KRISHNA'],
    hawkeye:['KRISHNA'],suryadev:['KRISHNA'],chandradev:['KRISHNA'],kabach:['KRISHNA'],mrityunjaya:['KABACH','KRISHNA'],
    vishwakarma:['SUDARSHAN'],'ui-guardian':['SUDARSHAN'],narad:['SUDARSHAN'],'project-perfection':['SUDARSHAN'],developer:['SUDARSHAN'],specialists:['SUDARSHAN']
  },
  output: {
    'rishi-council':['KRISHNA'],sudarshan:['KRISHNA','QA/QC'],research:['KRISHNA'],vision:['KRISHNA'],protection:['KRISHNA','SUDARSHAN'],
    brahma:['KRISHNA','BRAHMAGYAN'],brahmagyan:['KRISHNA','GYAN-BHANDAR'],'gyan-bhandar':['KRISHNA'],garuda:['GARUDANETRA','KRISHNA'],garudanetra:['KRISHNA'],
    hawkeye:['KRISHNA'],suryadev:['KRISHNA'],chandradev:['KRISHNA'],kabach:['MRITYUNJAYA','KRISHNA'],mrityunjaya:['SUDARSHAN','KRISHNA'],
    vishwakarma:['SUDARSHAN'],'ui-guardian':['KRISHNA'],narad:['KRISHNA'],'project-perfection':['KRISHNA'],developer:['SUDARSHAN'],specialists:['SUDARSHAN']
  },
  companies: [
    ['LR Resources',['resources','waste','e-waste','ewaste']],['LR Technology',['technology','software','ai','it']],['LR Production',['production','film','animation','media']],['LR Construction',['construction','renovation']],['LR Homes',['homes','residential']],['LR Foods',['foods','beverage']],['LR Agro',['agro','agriculture','farm']],['LR Commerce',['commerce','retail','wholesale','e-commerce','ecommerce']]
  ]
};
delete window.KRISHNA_BRAHMAND_DATA.nodes.canada_placeholder;
