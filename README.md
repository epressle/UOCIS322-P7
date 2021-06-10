# UOCIS322 - Project 7 - Ethan Pressley (epressle@uoregon.edu) #
Brevet time calculator with AJAX, MongoDB, a RESTful API, and authentication!

## Purpose ##
This project is intended to add a log in/log out system to the brevet calculator that has been worked on since Project 4, as well as add token authentication to the API; forbidding usage from non-signed-in persons.  
You can register an account using the 'register' button. Once registered, you can then sign in, which will authenticate you to access the database.  
You can log out after signing in by pressing the 'log out' button, in which you will lose authentication.  
The database form is nearly the same as project 6, besides the changes in the notes below.   
Other than these changes, the project is the same as project 6 and functions nearly identically.  
## NOTES ##
The token stays valid for 10 minutes, after which you will have to sign in again.  
All invalid entries for top k entries will return all entries.  
If the type of output (JSON, CSV) is somehow incorrectly set, the API will default to JSON.  
If none of the radio buttons are selected for types of output (listAll, listOpen, listClose), the API will default to listing all.
