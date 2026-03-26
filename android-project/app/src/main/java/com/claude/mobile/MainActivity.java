package com.claude.mobile;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebSettings;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResponse;
import android.webkit.MimeTypeMap;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import android.content.Context;

public class MainActivity extends Activity {
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        webView = new WebView(this);
        setContentView(webView);
        
        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setAllowFileAccess(true);
        webSettings.setAllowContentAccess(true);
        
        // Habilitar zoom
        webSettings.setSupportZoom(true);
        webSettings.setBuiltInZoomControls(true);
        webSettings.setDisplayZoomControls(false);
        
        // Configurar WebViewClient para cargar assets
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();
                
                // Cargar archivos desde assets
                if (url.startsWith("file:///android_asset/")) {
                    String path = url.substring(22); // Remove "file:///android_asset/"
                    try {
                        InputStream is = getAssets().open(path);
                        String mimeType = guessMimeType(path);
                        return new WebResourceResponse(mimeType, "UTF-8", is);
                    } catch (IOException e) {
                        return null;
                    }
                }
                
                // Para file:/// (rutas relativas), convertirlas a assets
                if (url.startsWith("file:///") && !url.contains("android_asset")) {
                    String path = url.substring(8); // Remove "file:///"
                    if (path.isEmpty() || path.equals("/")) {
                        path = "index.html";
                    }
                    try {
                        InputStream is = getAssets().open(path);
                        String mimeType = guessMimeType(path);
                        return new WebResourceResponse(mimeType, "UTF-8", is);
                    } catch (IOException e) {
                        // Intentar con index.html
                        try {
                            InputStream is2 = getAssets().open("index.html");
                            return new WebResourceResponse("text/html", "UTF-8", is2);
                        } catch (IOException e2) {
                            return null;
                        }
                    }
                }
                
                return null;
            }
        });
        
        // Cargar index.html desde assets
        webView.loadUrl("file:///android_asset/index.html");
    }
    
    private String guessMimeType(String path) {
        if (path.endsWith(".html")) return "text/html";
        if (path.endsWith(".css")) return "text/css";
        if (path.endsWith(".js")) return "application/javascript";
        if (path.endsWith(".json")) return "application/json";
        if (path.endsWith(".png")) return "image/png";
        if (path.endsWith(".jpg") || path.endsWith(".jpeg")) return "image/jpeg";
        if (path.endsWith(".svg")) return "image/svg+xml";
        if (path.endsWith(".woff") || path.endsWith(".woff2")) return "font/woff2";
        return "text/plain";
    }
    
    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
