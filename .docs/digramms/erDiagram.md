erDiagram
    Customer ||--o{ Rental : rents
    Instrument ||--o{ Rental : is_rented_by
    Rental ||--o{ RentalHistory : has_history

    Customer {
        int id
        string name
        string firstname
        string lastname
        string email
        string phone
        datetime created
    }

    Instrument {
        int id
        string name
        string brand
        string type
        string serial
        text description
        float price
        datetime created
        boolean is_available
    }

    Rental {
        int id
        int instrument_id
        int customer_id
        date start_date
        date end_date
        text description
        datetime created
    }

    RentalHistory {
        int id
        int rental_id
        int instrument_id
        text instrument_name
        int customer_id
        text customer_name
        datetime start_date
        datetime end_date
        text rental_note
        datetime timestamp
    }

    User {
        int id
        string username
        string email
        string password_hash
        boolean is_active
        int role
        string token
        datetime token_expiration
    }
