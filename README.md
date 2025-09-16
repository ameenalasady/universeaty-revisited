# Universeaty

> **Live Application: [universeaty.ca](https://universeaty.ca)**

Universeaty is a free, open-source web application designed to help McMaster University students secure a spot in their desired courses. It automates the tedious process of checking for open seats and provides timely notifications, ensuring you never miss an opportunity to enroll.

This repository represents a complete rewrite of the original project, built with modern technologies and professional software development practices for improved reliability, scalability, and maintainability.

---

## How It Works

The process is designed to be simple and intuitive. Universeaty acts as your personal automated assistant for course monitoring.

1.  **Select Your Term:** Choose the academic term (e.g., Fall 2024, Winter 2025) you are interested in.
2.  **Select Your Course:** A list of all courses available for that term will be loaded. Select the specific course you want to monitor.
3.  **View Section Availability:** The application will fetch and display all sections (lectures, tutorials, labs) for your chosen course, showing their current seat availability (Open/Full).
4.  **Watch a Section:** For any section that is currently full, click the "Watch" icon (eye symbol). You will be prompted to enter your email address.
5.  **Receive a Notification:** The Universeaty backend service will begin monitoring that section. As soon as a seat becomes available, you will receive an email notification, allowing you to register for the course immediately.

Your email is conveniently remembered in your browser's local storage to make watching multiple sections faster.

## Key Features

*   **Automated Monitoring:** The backend service checks for seat availability **every 60 seconds**, providing near real-time updates.
*   **Email Notifications:** Receive a clear and direct email the moment a spot opens up in a section you are watching.
*   **Simple & Clean Interface:** A minimalist user interface built for speed and ease of use, allowing you to set up a watch request in seconds.
*   **Reliable & Efficient:** The backend is designed to handle numerous requests efficiently and includes robust error handling. Course and term lists are updated periodically (typically hourly) to ensure accuracy.
*   **Privacy-Conscious:** Your email is used solely for sending you the notifications you request. It is not shared or used for any other purpose.
*   **Completely Open Source:** Both the frontend and backend code are available for review, ensuring full transparency in how the system operates.

## Frequently Asked Questions

**How do I know my watch request was successful?**
After you submit your email, you will see a confirmation message on the screen. From that point, the system is monitoring the section. You will only receive an email if and when a seat opens.

**What happens if a course or section is cancelled or removed by the university?**
If the system detects that a section you are watching no longer exists, your watch request for that specific section will be automatically deactivated to prevent false notifications.

**Can I watch multiple sections at once?**
Yes. You can create separate watch requests for as many different sections as you need.

## Important — MyTimetable login

Universeaty cannot perform live checks while McMaster's [MyTimetable](https://mytimetable.mcmaster.ca/) requires an authenticated login. Because this project does not have McMaster credentials, automated monitoring and live updates are temporarily suspended whenever MyTimetable prompts for sign-in. Monitoring will automatically resume as soon as the site becomes publicly accessible again (this typically resolves within a few days). We apologize for the inconvenience and appreciate your patience.

## Technical Overview

This project is a monorepo containing both the frontend client and the backend API.

#### Frontend

The user interface is a modern single-page application built for a fast and responsive user experience.

*   **Framework:** React with Vite
*   **Language:** TypeScript
*   **State Management:** TanStack Query (React Query) for server state caching and synchronization.
*   **UI Components:** shadcn/ui
*   **Styling:** Tailwind CSS

#### Backend

The backend is a lightweight yet powerful Flask API responsible for handling user requests, interacting with the database, checking for course availability, and sending notifications.

*   **Framework:** Flask
*   **Language:** Python
*   **Database:** SQLite for storing watch requests.
*   **Core Logic:** A multi-threaded service that periodically scrapes McMaster's official timetable data, compares it against active watch requests, and dispatches notifications.
*   **Notifications:** Emails are sent via SMTP.

## Contributing

Contributions are welcome! If you have suggestions for new features, improvements, or bug fixes, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the terms of the GNU AGPLv3. See the [LICENSE](LICENSE) file for the full license text.
