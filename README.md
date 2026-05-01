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
5.  **Manage Your Watches:** Access your personalized **Watch Dashboard** via a secure email link. Here you can view active monitors, see historical data, or cancel requests.
6.  **Receive a Notification:** The Universeaty backend service monitors sections every 15 seconds. As soon as a seat becomes available, you will receive an email notification.

## Key Features

*   **Real-Time Monitoring:** The backend service checks for seat availability **every 15 seconds**, providing industry-leading update speeds.
*   **Historical Seat Analytics:** Visualize seat availability trends over time with interactive charts, helping you decide when a spot is most likely to open up.
*   **Passwordless Dashboard:** Securely manage all your active watches in one place. No passwords required—just a one-click login link sent to your email.
*   **Batch Course Watching:** Interested in an entire course? Watch all closed sections (lectures, labs, tutorials) with a single click.
*   **Smart Search & Filters:** Quickly navigate through hundreds of courses with a responsive search interface and term-based filtering.
*   **Mobile-First Design:** A fully responsive UI polished for both desktop and mobile devices, allowing you to monitor courses on the go.
*   **Privacy-Conscious:** Your email is used solely for sending notifications and authentication links. It is never shared or used for marketing.

## Important — MyTimetable login

Universeaty cannot perform live checks while McMaster's [MyTimetable](https://mytimetable.mcmaster.ca/) requires an authenticated login. Because this project does not have McMaster credentials, automated monitoring and live updates are temporarily suspended whenever MyTimetable prompts for sign-in. Monitoring will automatically resume as soon as the site becomes publicly accessible again (this typically resolves within a few days).

## Technical Overview

This project is a monorepo containing both the frontend client and the backend API.

#### Frontend

A modern single-page application built for speed and a premium user experience.

*   **Framework:** React 19 with Vite
*   **Language:** TypeScript
*   **State Management:** TanStack Query (React Query) for server state.
*   **Visualization:** Recharts for historical seat analytics.
*   **UI Components:** shadcn/ui & Lucide Icons.
*   **Styling:** Tailwind CSS 4.0.

#### Backend

A high-performance Flask API designed for reliability and scale.

*   **Framework:** Flask
*   **Database:** SQLite for persistence, with **Redis** integration for robust rate limiting.
*   **Authentication:** Passwordless JWT-based authentication.
*   **Asynchronous Processing:** Threaded worker queue for decoupled, non-blocking email notifications.
*   **Core Logic:** Multi-threaded scraper that periodically fetches data from McMaster's official timetable, compares it against active watches, and dispatches alerts.

#### CI/CD & Code Quality

*   **CI:** Automated testing and build verification via GitHub Actions.
*   **Quality:** Pre-commit hooks using Husky and lint-staged.
*   **Linting/Formatting:** Ruff for Python, ESLint and Prettier for TypeScript/React.

## Contributing

Contributions are welcome! If you have suggestions for new features, improvements, or bug fixes, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the terms of the GNU AGPLv3. See the [LICENSE](LICENSE) file for the full license text.
