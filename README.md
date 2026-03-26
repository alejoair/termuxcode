# Guía: Convertir PWA a App Android con Bubblewrap en Termux

Esta guía documenta el proceso completo para convertir una Progressive Web App (PWA) en una aplicación Android nativa usando Bubblewrap directamente desde Termux en Android.

> **⚠️ AVISO IMPORTANTE**: Bubblewrap NO soporta oficialmente Termux/Android. Esta guía incluye parches y métodos alternativos para hacerlo funcionar completamente en Termux.
>
> **⚠️ LIMITACIÓN CRÍTICA**: El paquete `aapt` de Termux NO es un aapt2 real y no puede procesar recursos Android correctamente. Gradle fallará en la etapa de `processReleaseResources`. Ver las **Soluciones Alternativas** al final.
>
> **ÚLTIMA ACTUALIZACIÓN**: 2026-03-26 - Probado en Termux Android 14

---

## Resumen

### Lo que funciona
- ✅ Configuración de Android SDK
- ✅ Configuración de Gradle
- ✅ Compilación de código Java
- ✅ Preparación de manifiestos y recursos XML

### Lo que NO funciona
- ❌ AAPT2 en Termux (el `aapt` de Termux no es un aapt2 real)
- ❌ Compilación completa de APK con Gradle en Termux
- ❌ Procesamiento de recursos PNG con aapt2

---

## Pasos que funcionan (para referencia)

### Paso 1: Instalar Java 17

```bash
pkg install openjdk-17 -y
/data/data/com.termux/files/usr/lib/jvm/java-17-openjdk/bin/java -version
```

### Paso 2: Android SDK

```bash
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
mkdir -p ~/android-sdk/cmdline-tools
unzip -q commandlinetools-linux-*.zip -d ~/android-sdk/cmdline-tools
mv ~/android-sdk/cmdline-tools/cmdline-tools ~/android-sdk/cmdline-tools/latest

export ANDROID_HOME=$HOME/android-sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools
```

### Paso 3: Instalar componentes Android

```bash
yes | sdkmanager "platforms;android-34" "build-tools;34.0.0" "platform-tools"
```

### Paso 4: Gradle

```bash
pkg install gradle -y
```

### Paso 5: Parchear Bubblewrap (opcional)

```bash
npm install -g @bubblewrap/cli

# Parches para Termux
sed -i "s/case 'linux':/case 'linux':\n            case 'android':/" \
  /data/data/com.termux/files/usr/lib/node_modules/@bubblewrap/cli/dist/lib/AndroidSdkToolsInstaller.js

sed -i "s/process.platform === 'linux' || process.platform === 'win32'/process.platform === 'linux' || process.platform === 'android' || process.platform === 'win32'/" \
  /data/data/com.termux/files/usr/lib/node_modules/@bubblewrap/cli/node_modules/@bubblewrap/core/dist/lib/jdk/JdkHelper.js

mkdir -p ~/.bubblewrap
cat > ~/.bubblewrap/config.json << 'EOF'
{
  "jdkPath": "/data/data/com.termux/files/usr/lib/jvm/java-17-openjdk",
  "androidSdkPath": "/data/data/com.termux/files/home/android-sdk"
}
EOF
```

---

## Soluciones Alternativas

### Opción 1: Usar apktool en Termux (RECOMENDADO)

`apktool` es más compatible con Termux y puede compilar APKs sin el aapt2 oficial.

```bash
pkg install apktool -y
```

Proceso básico:
1. Descompilar un APK base con `apktool d base.apk`
2. Modificar recursos y manifiesto
3. Recompilar con `apktool b output_dir -o nueva.apk`
4. Firmar con `jarsigner` o `apksigner`

### Opción 2: WebView Nativo Simple

Crear una app WebView mínima que no requiera recursos complejos:

**MainActivity.java**:
```java
package com.ejemplo.app;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebSettings;

public class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        WebView webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        webView.loadUrl("file:///path/to/your/index.html");
        setContentView(webView);
    }
}
```

**AndroidManifest.xml**:
```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <application android:label="Mi App">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

### Opción 3: Compilar en otra plataforma

1. Desarrollar el proyecto en Termux
2. Transferir el proyecto a una PC Linux/Mac/Windows
3. Compilar allí con Gradle
4. Transferir el APK de vuelta a Termux/Android

```bash
# En PC:
gradle assembleRelease
adb push app/build/outputs/apk/release/app-release.apk /sdcard/
```

### Opción 4: Usar GitHub Actions

Crear un workflow que compile el proyecto automáticamente:

```yaml
name: Build Android APK
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup JDK
        uses: actions/setup-java@v3
        with:
          java-version: '17'
          distribution: 'temurin'
      - name: Build APK
        run: |
          ./gradlew assembleRelease
      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: app-release
          path: app/build/outputs/apk/release/*.apk
```

### Opción 5: Usar un aapt2 ARM compilado

Si puedes obtener un aapt2 real compilado para ARM64:

1. Descargar desde un proyecto de terceros que compile aapt2 para ARM
2. Colocarlo en `~/.gradle/caches/.../transformed/aapt2-*/aapt2`
3. Asegurar permisos de ejecución

**NOTA**: El paquete `aapt` en Termux NO es un aapt2, es una versión reducida que no soporta todas las funciones necesarias.

---

## Estructura de proyecto WebView mínimo

```
android-project/
├── build.gradle (configuración simplificada)
├── settings.gradle
├── gradle.properties
├── app/
│   ├── build.gradle (WebView, sin dependencias externas)
│   └── src/
│       └── main/
│           ├── AndroidManifest.xml
│           ├── java/com/ejemplo/app/MainActivity.java
│           └── res/
│               ├── values/strings.xml
│               ├── drawable/ic_launcher.xml (vector, no PNG)
│               └── mipmap-anydpi-v26/ic_launcher.xml (vector)
└── android.keystore
```

---

## Troubleshooting

### "aapt2: Syntax error: Unterminated quoted string"
El `aapt` de Termux no es compatible con aapt2. Use una de las soluciones alternativas.

### "Daemon startup failed"
AAPT2 daemon no puede ejecutarse en Termux. Las opciones de gradle no resuelven esto porque el binario subyacente es incorrecto.

### Build avanza pero falla en processReleaseResources
El código Java compila pero los recursos no pueden procesarse. Confirma que estás usando recursos XML vectoriales, no PNG.

---

## Conclusión

**La compilación completa de APK con Gradle en Termux NO es actualmente viable** debido a la falta de un aapt2 nativo para ARM64.

Para convertir una PWA a app Android desde Termux, se recomienda:
1. **Usar apktool** (Opción 1)
2. **Compilar en otra plataforma** (Opción 3)
3. **Usar GitHub Actions** (Opción 4)

---

## Referencias

- [Bubblewrap Documentation](https://github.com/GoogleChromeLabs/bubblewrap)
- [apktool](https://ibotpeaches.github.io/Apktool/)
- [Android Gradle Plugin](https://developer.android.com/studio/build)
- [AAPT2](https://developer.android.com/studio/command-line/aapt2)
