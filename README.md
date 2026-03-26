# Guía: Convertir PWA a App Android desde Termux

**Método funcional probado:** WebView + GitHub Actions para compilación remota.

> **⚠️ PROBLEMA:** El `aapt` de Termux NO es un aapt2 real. Gradle fallará en Termux al compilar recursos.
>
> **✅ SOLUCIÓN:** Usar GitHub Actions para compilar en servidores x86 gratis. Todo desde el celular, sin PC.

---

## Resumen del Flujo

```
Termux (desarrollo) → Push a GitHub → GitHub Actions compila → Descargar APK → Instalar
```

---

## Paso 1: Crear Repositorio GitHub

```bash
# Instalar gh CLI
pkg install gh -y

# Autenticarse
gh auth login

# Crear repo
gh repo create mi-app --public --source=. --remote=origin
```

---

## Paso 2: Crear Proyecto Android

```bash
# Estructura de carpetas
mkdir -p android-project/app/src/main/{assets,java/com/miapp}
cd android-project
```

### 2.1 Archivos Gradle

**`build.gradle`** (raíz):
```gradle
buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath 'com.android.tools.build:gradle:8.2.0'
    }
}

task clean(type: Delete) {
    delete rootProject.buildDir
}
```

**`settings.gradle`**:
```gradle
pluginManagement {
    repositories {
        google()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.PREFER_SETTINGS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "MiApp"
include ':app'
```

**`gradle.properties`**:
```properties
android.useAndroidX=true
android.enableJetifier=true
```

### 2.2 App build.gradle

**`app/build.gradle`**:
```gradle
plugins {
    id 'com.android.application'
}

android {
    namespace 'com.miapp.miapp'
    compileSdk 34

    defaultConfig {
        applicationId "com.miapp.miapp"
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName "1.0"
    }

    buildTypes {
        release {
            minifyEnabled false
        }
    }

    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
}

dependencies {
    // Sin dependencias externas - WebView puro
}
```

### 2.3 MainActivity.java

**`app/src/main/java/com/miapp/miapp/MainActivity.java`**:
```java
package com.miapp.miapp;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebSettings;
import android.webkit.WebViewClient;

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

        webView.setWebViewClient(new WebViewClient());

        // Cargar HTML desde assets
        webView.loadUrl("file:///android_asset/index.html");
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
```

### 2.4 AndroidManifest.xml

**`app/src/main/AndroidManifest.xml`**:
```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="Mi App"
        android:theme="@android:style/Theme.Material.Light.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

### 2.5 Agregar Assets (HTML, CSS, JS)

```bash
# Copiar tu PWA a assets
cp -r /ruta/a/tu/pwa/* android-project/app/src/main/assets/

# Estructura mínima:
# app/src/main/assets/
#   ├── index.html
#   ├── app.js
#   ├── styles.css
#   └── manifest.json
```

### 2.6 Iconos (opcional)

Usa drawables vectoriales XML para evitar problemas con PNG:

**`app/src/main/res/drawable/ic_launcher.xml`**:
```xml
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path android:fillColor="#1a1a2e"
        android:pathData="M0,0h108v108h-108z" />
</vector>
```

---

## Paso 3: GitHub Actions Workflow

Crear `.github/workflows/build-apk.yml`:

```yaml
name: Build Android APK

on:
  push:
    branches: [ main ]
  workflow_dispatch:  # Permite ejecutar manualmente

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: Setup Android SDK
        uses: android-actions/setup-android@v3
        with:
          api-level: 34
          build-tools: 34.0.0

      - name: Build APK
        run: |
          cd android-project
          gradle wrapper --gradle-version 8.5
          ./gradlew assembleRelease

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: App-APK
          path: android-project/app/build/outputs/apk/release/app-release.apk
          retention-days: 90
```

---

## Paso 4: Compilar y Obtener APK

```bash
# Subir cambios
git add .
git commit -m "Add Android project"
git push origin main

# Esperar a que termine el workflow (1-2 min)
gh run list --limit 1

# Descargar APK
gh run download --name App-APK -D ~/Downloads

# Copiar a ubicación accesible desde Android
cp ~/Downloads/app-release.apk /sdcard/Download/MiApp.apk
```

---

## Paso 5: Instalar en el Móvil

1. Abrir **Archivos**
2. Ir a **Descargas**
3. Tocar `MiApp.apk`
4. Instalar

---

## Modificar la App

Para hacer cambios:

```bash
# 1. Editar archivos en android-project/app/src/main/assets/
nano android-project/app/src/main/assets/index.html

# 2. Subir cambios
git add .
git commit -m "Update UI"
git push origin main

# 3. Esperar build y descargar nuevo APK
gh run download --name App-APK -D ~/Downloads
```

---

## Estructura Final

```
mi-proyecto/
├── .github/
│   └── workflows/
│       └── build-apk.yml
├── android-project/
│   ├── app/
│   │   ├── build.gradle
│   │   └── src/
│   │       └── main/
│   │           ├── AndroidManifest.xml
│   │           ├── assets/          ← Tu PWA va aquí
│   │           │   ├── index.html
│   │           │   ├── app.js
│   │           │   └── styles.css
│   │           ├── java/com/miapp/
│   │           │   └── MainActivity.java
│   │           └── res/
│   │               ├── values/
│   │               └── drawable/
│   ├── build.gradle
│   ├── settings.gradle
│   └── gradle.properties
└── README.md
```

---

## Comandos Útiles con gh CLI

```bash
# Ver estado del último build
gh run view --log

# Disparar build manualmente
gh workflow run build-apk.yml

# Ver todos los builds
gh run list

# Descargar APK de un build específico
gh run download <run-id> --name App-APK
```

---

## Troubleshooting

### "The webpage could not be loaded"
- **Causa:** Ruta de archivo incorrecta o assets no incluidos
- **Solución:** Asegúrate de copiar archivos a `app/src/main/assets/` y que `MainActivity.java` use `file:///android_asset/index.html`

### "Build failed"
- Verifica los logs: `gh run view --log-failed`
- Errores comunes: sintaxis de Java, nombres de paquete incorrectos

### APK no instala
- Desinstala la versión anterior primero
- Habilita "Fuentes desconocidas" en Ajustes de seguridad

---

## Ventajas de este Método

| Aspecto | Termux Directo | GitHub Actions |
|---------|----------------|----------------|
| **Compilación** | ❌ No funciona (aapt2) | ✅ Servidores x86 gratis |
| **Velocidad** | - | ~1-2 min |
| **PC requerida** | ❌ Sí | ❌ No |
| **Costo** | Gratis | Gratis |
| **Assets en APK** | Difícil | Fácil |

---

## Referencias

- [GitHub Actions](https://docs.github.com/en/actions)
- [WebView Android](https://developer.android.com/guide/webapps/webview)
- [GitHub CLI](https://cli.github.com/manual/)
