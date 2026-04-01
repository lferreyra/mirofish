export default {
  common: {
    start: 'Start',
    back: 'Back',
    next: 'Next',
    cancel: 'Cancel',
    confirm: 'Confirm',
    upload: 'Upload',
    download: 'Download',
    delete: 'Delete',
    save: 'Save',
    edit: 'Edit',
    view: 'View',
    loading: 'Loading...',
    processing: 'Processing',
    completed: 'Completed',
    error: 'Error',
    success: 'Success',
    status: 'Status',
    settings: 'Settings',
    help: 'Help',
    about: 'About'
  },
  home: {
    nav: {
      github: 'Visit our GitHub page'
    },
    hero: {
      tag: 'Simple and Universal Swarm Intelligence Engine',
      version: '/ v0.1-beta',
      title: 'Upload Any Report',
      titleHighlight: 'Predict the Future Instantly',
      desc: 'Even with just a piece of text, <span class="highlight-bold">MiroFish</span> can automatically generate a parallel world with up to <span class="highlight-orange">millions of Agents</span> based on the real-world seeds it contains. Inject variables from a god\'s-eye view and find <span class="highlight-code">"local optimal solutions"</span> in complex group interactions.',
      slogan: 'Rehearse the future in Agent groups, win decisions after hundreds of battles<span class="blinking-cursor">_</span>'
    },
    systemStatus: {
      title: 'System Status',
      ready: 'Ready',
      readyDesc: 'Prediction engine on standby, ready to upload multiple unstructured data to initialize simulation sequence',
      metrics: {
        lowCost: 'Low Cost',
        lowCostDesc: 'Average $5 per simulation',
        highAvailability: 'High Availability',
        highAvailabilityDesc: 'Up to millions of Agent simulations'
      }
    },
    workflow: {
      title: 'Workflow Sequence',
      steps: [
        {
          title: 'Graph Construction',
          desc: 'Real-world seed extraction & individual and group memory injection & GraphRAG construction'
        },
        {
          title: 'Environment Setup',
          desc: 'Entity relationship extraction & persona generation & environment configuration Agent injection simulation parameters'
        },
        {
          title: 'Start Simulation',
          desc: 'Dual platform parallel simulation & automatic parsing of prediction requirements & dynamic update of temporal memory'
        },
        {
          title: 'Report Generation',
          desc: 'Report Agent has rich toolset for deep interaction with post-simulation environment'
        },
        {
          title: 'Deep Interaction',
          desc: 'Chat with anyone in the simulated world & interact with Report Agent'
        }
      ]
    },
    console: {
      upload: {
        label: '01 / Real-world Seeds',
        formats: 'Supported formats: PDF, MD, TXT',
        dragTitle: 'Drag files to upload',
        dragHint: 'Or click to browse file system',
        uploadedFiles: 'Uploaded files'
      },
      input: {
        label: '>_ 02 / Simulation Prompt',
        placeholder: '// Enter simulation or prediction requirements in natural language (e.g. What public opinion trend would be triggered if Wuhan University announces revoking Xiao\'s punishment)',
        engine: 'Engine: MiroFish-V1.0'
      },
      button: {
        start: 'Start Engine',
        initializing: 'Initializing...'
      }
    }
  },
  main: {
    viewModes: {
      graph: 'Graph',
      split: 'Split',
      workbench: 'Workbench'
    },
    steps: [
      'Graph Construction',
      'Environment Setup',
      'Start Simulation',
      'Report Generation',
      'Deep Interaction'
    ],
    status: {
      ready: 'Ready',
      error: 'Error',
      building: 'Building Graph',
      generating: 'Generating Ontology',
      initializing: 'Initializing'
    }
  },
  components: {
    step1: {
      title: 'Graph Construction',
      status: {
        initializing: 'Initializing...',
        uploading: 'Uploading and analyzing documents...',
        generating: 'Generating ontology...',
        building: 'Building knowledge graph...',
        completed: 'Graph construction completed',
        failed: 'Graph construction failed'
      },
      buttons: {
        nextStep: 'Next Step: Environment Setup'
      }
    },
    step2: {
      title: 'Environment Setup',
      description: 'Configure simulation environment and agent personas',
      buttons: {
        startSimulation: 'Start Simulation',
        goBack: 'Go Back'
      }
    },
    step3: {
      title: 'Start Simulation',
      description: 'Run multi-agent simulation',
      buttons: {
        nextStep: 'Next Step: Report Generation'
      }
    },
    step4: {
      title: 'Report Generation',
      description: 'Generate analysis report from simulation results',
      buttons: {
        nextStep: 'Next Step: Deep Interaction'
      }
    },
    step5: {
      title: 'Deep Interaction',
      description: 'Chat with agents and explore the simulated world',
      buttons: {
        chat: 'Start Chat'
      }
    },
    history: {
      title: 'Project History',
      empty: 'No projects yet',
      open: 'Open Project',
      delete: 'Delete Project'
    }
  },
  errors: {
    noFiles: 'No files selected',
    noPrompt: 'Please enter simulation requirements',
    uploadFailed: 'File upload failed',
    networkError: 'Network error, please try again',
    unknownError: 'Unknown error occurred'
  }
}
