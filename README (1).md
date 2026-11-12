# Route Racer --- Dijkstra's Shortest Path Game

Route Racer is an interactive browser-based game that teaches
**Dijkstra's shortest path algorithm** using a road network of Indian
cities. The shortest-path calculations run in Python, while the browser
displays the map, gameplay, and algorithm visualisation.

## Features

-   **Play mode:** Complete five route challenges by travelling from a
    start city to a destination city using the shortest total distance.
-   **Dijkstra visualiser:** Watch the algorithm explore the graph step
    by step, or let it play automatically. Adjust the animation speed.
-   **Explorer mode:** Find the shortest route between two selected
    cities, or view the shortest distances and paths from one source to
    every city.
-   **Interactive map:** Displays the cities, road connections,
    distances in kilometres, and highlighted routes.
-   **Game scoring:** Earn points based on how close your route is to
    the optimal route. Perfect routes receive a bonus, while hints
    reduce the score.
-   **Best score:** The browser stores the best score locally when local
    storage is available.

## Technologies Used

-   Python 3
-   Python standard-library modules: `heapq`, `json`, `random`,
    `threading`, `time`, `webbrowser`, `http.server`, and `urllib.parse`
-   HTML, CSS, and JavaScript for the browser interface
-   SVG for drawing the map

No third-party Python packages are required.

## Requirements

-   Python 3 installed on your computer
-   A modern web browser
-   The project Python file, `daa_project.py`

## How to Run

1.  Download or save `daa_project.py` to a folder on your computer.

2.  Open Command Prompt or a terminal in that folder.

3.  Run:

    ``` bash
    python daa_project.py
    ```

    On some systems, use:

    ``` bash
    python3 daa_project.py
    ```

4.  The program starts a local web server and opens the game in your
    default browser.

5.  If the browser does not open automatically, copy the local URL
    printed in the terminal and open it in your browser.

The game runs locally on your computer. Keep the terminal window open
while playing.

## How to Play

1.  Select **Play** and click **Start game**.
2.  Each round gives you a start city and a destination city.
3.  Click a highlighted neighbouring city on the map to travel along a
    road.
4.  Reach the destination while keeping the total road distance as low
    as possible.
5.  Use **Undo** to reverse your last move, **Restart route** to start
    the route again, or **Hint** to reveal the recommended next city (a
    10-point penalty applies).
6.  After reaching the destination, compare your route with the shortest
    route calculated by Dijkstra's algorithm.
7.  Complete all five rounds to see your final score.

Other tabs:

-   **Watch Dijkstra:** Choose a source city and optionally a
    destination, then use Play, Step, or Reset to inspect the algorithm.
-   **Explorer:** Choose source and destination cities to calculate a
    shortest route. Leave the destination set to "all cities" to see
    shortest paths from the selected source to every city.

## Cities and Road Network

The graph contains these 14 cities:

Chandigarh, Delhi, Jaipur, Agra, Lucknow, Bhopal, Ahmedabad, Mumbai,
Pune, Nagpur, Hyderabad, Bengaluru, Chennai, and Kolkata.

Roads are represented as **undirected weighted edges**. The weights are
approximate distances in kilometres, as defined in the `ROADS` list in
the Python source code. The map coordinates are used only to display the
cities.

## Algorithm: Dijkstra's Shortest Path

The project represents the road network as an adjacency list. Since
roads are undirected, each road is added in both directions.

Dijkstra's algorithm calculates the minimum distance from a source city
to all reachable cities:

1.  Set the source distance to 0 and all other distances to infinity.
2.  Insert the source into a priority queue (min-heap).
3.  Remove the city with the smallest tentative distance.
4.  Check each neighbouring city. If travelling through the current city
    gives a shorter distance, update the neighbour's distance and
    parent.
5.  Continue until the priority queue is empty.
6.  Follow the parent links to reconstruct a shortest path.

The implementation uses Python's `heapq` priority queue. With an
adjacency list and a binary heap, the usual time complexity is **O((V +
E) log V)**, where `V` is the number of vertices (cities) and `E` is the
number of edges (roads).

Dijkstra's algorithm assumes non-negative edge weights. The road
distances in this project are positive.

## Project Structure

``` text
project-folder/
├── daa_project.py   # Python algorithm, local web server, and embedded web interface
└── README.md        # Project documentation
```

The HTML, CSS, and JavaScript interface are embedded in the Python file,
so no separate frontend files are needed.

## Stopping the Game

-   Click the **Exit** button in the game, or
-   Press **Ctrl+C** in the terminal.

## Notes

-   Road distances are approximate sample data for demonstrating the
    algorithm; they are not live navigation or traffic distances.
-   The local server binds to `127.0.0.1`, so it is intended for use on
    the same computer.
-   The Python file chooses an available local port automatically.

## Author

Add your name, class, roll number, and institution details here before
submitting the project.
