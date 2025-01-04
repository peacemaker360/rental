classDiagram
    class Customer {
        -id : Integer
        -name : String
        -firstname : String
        -lastname : String
        -email : String
        -phone : String
        -created : DateTime
        +search_customers(keyword) : List[Customer]
    }

    class Instrument {
        -id : Integer
        -name : String
        -brand : String
        -type : String
        -serial : String
        -description : Text
        -price : Float
        -created : DateTime
        -is_available : Boolean
        +is_available() : Boolean
        +search_instruments(keyword) : List[Instrument]
    }

    class Rental {
        -id : Integer
        -instrument_id : Integer
        -customer_id : Integer
        -start_date : Date
        -end_date : Date
        -description : Text
        -created : DateTime
        +search_rentals(keyword) : List[Rental]
    }

    class RentalHistory {
        -id : Integer
        -rental_id : Integer
        -instrument_id : Integer
        -instrument_name : Text
        -customer_id : Integer
        -customer_name : Text
        -start_date : DateTime
        -end_date : DateTime
        -rental_note : Text
        -timestamp : DateTime
        +search_rentalshistory(keyword) : List[RentalHistory]
        +getBy_instrumentId(id) : List[RentalHistory]
        +getBy_customerId(id) : List[RentalHistory]
    }

    class User {
        -id : Integer
        -username : String
        -email : String
        -password_hash : String
        -is_active : Boolean
        -role : Integer
        -token : String
        -token_expiration : DateTime
        +set_password(password) : Void
        +check_password(password) : Boolean
        +get_reset_password_token(expires_in) : String
        +verify_reset_password_token(token) : User
        +get_token(expires_in) : String
        +revoke_token() : Void
        +check_token(token) : User
        +to_json() : Dict
        +to_dict(include_email) : Dict
        +from_dict(data, new_user) : Void
        +to_collection() : Dict
    }

    Customer "1" -- "0..*" Rental : rental
    Instrument "1" -- "0..*" Rental : rental
    Rental "1" -- "0..*" RentalHistory : rental
