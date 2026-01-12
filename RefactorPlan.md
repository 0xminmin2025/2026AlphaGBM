This project needs to be refactored. 

This project's entry point is: home/index.html

/stock path points to templates/index.html (maybe need to be changed file name)
/options path should points to templates/options.html (it's backend service is maintained under ./new_options_module)
/pricing and /profile is for subscription and also user profile management.

the user signup/signin is provided by supabase including user auth.
the payment part is based on stripe.

You need to understand the whole project, and use react to refactor the project, in typescript

You need to complete some product features that might not be completed, such as subscription status and payment history in user profile., subscription management, etc.

The backend code and frontend code should be separated. backend code should still be in python, while the frontend code should be in react written in typescript.

The UI should be modern and consistent, with some main color / secondary color / text color / background color configurable in a file.

The website can be in Chinese / English. maintain intl config file for i18n.

consider use shadcn ui for ui components, and make sure the style and color style is the same just like the current, but more user friendly. consider web mobile adaptive. 


PUT all refactor code under ./refactor folder, don't remove and change any code of the current project. but just write the whole project under ./refactor folder.

Make sure the new refactor code is clean and well structure, and easy to maintain. and all parameters can be easily configurable.

The .env file has the credentials we need. and new_options_module/tiger_openapi_config.properties new_options_module/tiger_openapi_token.properties is the credentials for tiger openapi. 


understand the whole project, and complete the refactor, and make it a complete and well designed and good user experience web app.

if you find some feature not completed or missing some logic, or design not good. please complete it or fix it.