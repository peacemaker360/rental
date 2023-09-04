flowchart LR

    Start[Start] --> Login[User Login]
    Login --> KundeAkt[Start Kunde-Aktivitäten]
    Login --> InstrumentAkt[Start Instrument-Aktivitäten]
    Login --> VerleihAkt[Start Verleih-Aktivitäten]
    Login --> VerleihhistAkt[Start Verleihhistorie-Aktivitäten]

    subgraph "Kunde-Aktivitäten"
        KundeAkt --> KundeErst[Kunde erstellen]
        KundeAkt --> KundeAnz[Kunde anzeigen]
        KundeAkt --> KundeBearb[Kunde bearbeiten]
        KundeAkt --> KundeLöschen[Kunde löschen]
    end

    subgraph "Instrument-Aktivitäten"
        InstrumentAkt --> InstErst[Instrument erstellen]
        InstrumentAkt --> InstAnz[Instrument anzeigen]
        InstAnz --> VerfügPrüf[Überprüfung der Verfügbarkeit]
        InstrumentAkt --> InstBearb[Instrument bearbeiten]
        InstrumentAkt --> InstLöschen[Instrument löschen]
    end

    subgraph "Verleih-Aktivitäten"
        VerleihAkt --> VerleihErst[Verleih erstellen]
        VerleihErst --> VerfügPrüfVerleih[Überprüfung der Verfügbarkeit des Instruments]
        VerfügPrüfVerleih --> VerfügDecision{Verfügbar?}
        VerfügDecision --> VerleihAnz[Verleih anzeigen]
        VerleihAnz --> VerleihBearb[Verleih bearbeiten]
        VerleihAnz --> VerleihEnd[Verleih beenden/löschen]
    end

    subgraph "Verleihhistorie-Aktivitäten"
        VerleihhistAkt --> VerleihhistAnz[Verleihhistorie anzeigen]
    end

    style KundeLöschen fill:#f9d,stroke:#333,stroke-width:2px
    style InstLöschen fill:#f9d,stroke:#333,stroke-width:2px
    style VerleihEnd fill:#f9d,stroke:#333,stroke-width:2px
    style VerleihhistAnz fill:#f9d,stroke:#333,stroke-width:2px
