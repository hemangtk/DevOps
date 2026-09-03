// Hello World web app - Java (built-in com.sun.net.httpserver, no framework needed)
// Name: Hemang | Enrollment number: 24bcs10209
import com.sun.net.httpserver.HttpServer;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

public class Main {
    public static void main(String[] args) throws Exception {
        int port = 8000;

        String page = """
            <!doctype html>
            <html><head><meta charset="utf-8"><title>Java in Docker</title>
            <style>body{font-family:system-ui,sans-serif;display:grid;place-items:center;height:100vh;margin:0;background:#111;color:#eee}
            h1{font-size:3rem;margin:0}p{color:#8cc}</style></head>
            <body><div><h1>Hello World</h1>
            <p>Java %s &middot; running in Docker</p>
            <p>Hemang &middot; 24bcs10209</p></div></body></html>
            """.formatted(System.getProperty("java.version"));

        HttpServer server = HttpServer.create(new InetSocketAddress("0.0.0.0", port), 0);
        server.createContext("/", exchange -> {
            byte[] body = page.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "text/html; charset=utf-8");
            exchange.sendResponseHeaders(200, body.length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(body);
            }
        });
        server.setExecutor(null);
        server.start();
        System.out.println("Java app listening on http://0.0.0.0:" + port);
    }
}
