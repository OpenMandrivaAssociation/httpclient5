Name:		httpclient5
Version:	5.6.5
Release:	1
Summary:	Apache HTTP client
Group:		Development/Java
License:	Apache-2.0
URL:		https://hc.apache.org/httpcomponents-client-5.6.x/
%global httpcorever 5.4.4
%global slf4jver 1.7.36
%global compressver 1.28.0
%global zstdver 1.5.7-4
%global brotliver 1.20.0
Source0:	https://archive.apache.org/dist/httpcomponents/httpclient/source/httpcomponents-client-%{version}-src.tar.gz
Source1:	https://repo1.maven.org/maven2/com/github/luben/zstd-jni/%{zstdver}/zstd-jni-%{zstdver}-sources.jar
Source2:	https://repo1.maven.org/maven2/com/aayushatharva/brotli4j/brotli4j/%{brotliver}/brotli4j-%{brotliver}-sources.jar
BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	javapackages-filesystem
BuildRequires:	sysjar
BuildRequires:	httpcore5 >= %{httpcorever}
BuildRequires:	httpcore5-h2 >= %{httpcorever}
BuildRequires:	slf4j >= %{slf4jver}
BuildRequires:	apache-commons-compress >= %{compressver}
Requires:	java-current
Requires:	httpcore5 >= %{httpcorever}
Requires:	httpcore5-h2 >= %{httpcorever}
Requires:	slf4j >= %{slf4jver}

%description
Apache HttpClient %{version} is the HTTP client built on HttpCore
%{httpcorever}. The classes live in org.apache.hc.client5. This
package ships the httpclient5 jar. The cache, fluent, and observation
modules from the same source tree are not included. HttpClient 4
stays in httpcomponents-client.

%{version} builds against HttpCore %{httpcorever}. It stops concurrent
HTTP/2 request-body replay, and it closes a connection-pool leak in
ResponseEntityProxy when disconnecting the endpoint throws. Public
suffix checks decode punycode names before matching the list. Brotli
decompression no longer hangs on a large input buffer.

Conscrypt, Brotli, and zstd are optional. This build compiles the
call sites against stubs and the upstream Java sources of those
libraries. Those compile-only classes are not installed. Commons
Compress is optional at runtime.

%prep
# The Apache source archive has no top-level directory.
%autosetup -c -n httpcomponents-client-%{version}
find . -name '*.jar' -delete
find . -name '*.class' -delete

%build
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java}"
mkdir -p build/zstd-src build/brotli-src build/stub/org/conscrypt \
	build/zstd-classes build/brotli-classes build/stub-classes build/classes

# zstd-jni ships no generated ZstdVersion. The class is compile-only.
( cd build/zstd-src && "$JAVA_HOME/bin/jar" xf %{SOURCE1} )
mkdir -p build/zstd-src/com/github/luben/zstd/util
cat > build/zstd-src/com/github/luben/zstd/util/ZstdVersion.java << 'EOF'
package com.github.luben.zstd.util;
final class ZstdVersion {
    static final String VERSION = "%{zstdver}";
}
EOF
find build/zstd-src -name '*.java' > build/zstd.list
test -s build/zstd.list
"$JAVA_HOME/bin/javac" --release 8 -proc:none -encoding UTF-8 \
	-d build/zstd-classes @build/zstd.list
"$JAVA_HOME/bin/jar" cf build/zstd-compile.jar -C build/zstd-classes .

# Brotli4j's Netty helpers and native-service type are not called by
# HttpClient. Drop those files and compile the rest as a stub jar.
( cd build/brotli-src && "$JAVA_HOME/bin/jar" xf %{SOURCE2} )
rm -f build/brotli-src/com/aayushatharva/brotli4j/decoder/Decoders.java \
	build/brotli-src/com/aayushatharva/brotli4j/encoder/Encoders.java
test ! -e build/brotli-src/com/aayushatharva/brotli4j/decoder/Decoders.java
mkdir -p build/brotli-src/com/aayushatharva/brotli4j/service \
	build/brotli-src/com/aayushatharva/brotli4j/decoder
cat > build/brotli-src/com/aayushatharva/brotli4j/decoder/DirectDecompress.java << 'EOF'
package com.aayushatharva.brotli4j.decoder;
final class DirectDecompress {
    DirectDecompress(DecoderJNI.Status resultStatus, byte[] decompressedData, Object ignored) {
    }
}
EOF
cat > build/brotli-src/com/aayushatharva/brotli4j/service/BrotliNativeProvider.java << 'EOF'
package com.aayushatharva.brotli4j.service;
public interface BrotliNativeProvider {
    String platformName();
}
EOF
find build/brotli-src -name '*.java' > build/brotli.list
test -s build/brotli.list
"$JAVA_HOME/bin/javac" --release 8 -proc:none -encoding UTF-8 \
	-d build/brotli-classes @build/brotli.list
"$JAVA_HOME/bin/jar" cf build/brotli-compile.jar -C build/brotli-classes .

cat > build/stub/org/conscrypt/Conscrypt.java << 'EOF'
package org.conscrypt;
import javax.net.ssl.SSLEngine;
public final class Conscrypt {
    private Conscrypt() {}
    public static boolean isConscrypt(SSLEngine engine) {
        return false;
    }
    public static void setApplicationProtocols(SSLEngine engine, String[] protocols) {
    }
    public static String getApplicationProtocol(SSLEngine engine) {
        return null;
    }
}
EOF
cat > build/stub/org/conscrypt/Internal.java << 'EOF'
package org.conscrypt;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
@Retention(RetentionPolicy.CLASS)
public @interface Internal {}
EOF
"$JAVA_HOME/bin/javac" --release 8 -proc:none -encoding UTF-8 \
	-d build/stub-classes build/stub/org/conscrypt/Conscrypt.java \
	build/stub/org/conscrypt/Internal.java
"$JAVA_HOME/bin/jar" cf build/conscrypt-stub.jar -C build/stub-classes .

sed -i \
	-e 's|${project.artifactId}|httpclient5|' \
	-e 's|${project.version}|%{version}|' \
	httpclient5/src/main/resources/org/apache/hc/client5/version.properties
grep -F -q 'info.release   = %{version}' \
	httpclient5/src/main/resources/org/apache/hc/client5/version.properties
find httpclient5/src/main/java -name '*.java' > build/sources.list
test -s build/sources.list
"$JAVA_HOME/bin/javac" --release 8 -proc:none -encoding UTF-8 \
	-cp "%{_javadir}/httpcore5.jar:%{_javadir}/httpcore5-h2.jar:%{_javadir}/slf4j/slf4j-api.jar:%{_javadir}/commons-compress.jar:build/zstd-compile.jar:build/brotli-compile.jar:build/conscrypt-stub.jar" \
	-d build/classes @build/sources.list
test ! -e build/classes/org/conscrypt/Conscrypt.class
test ! -e build/classes/org/conscrypt/Internal.class
test ! -e build/classes/com/github/luben/zstd/Zstd.class
test ! -e build/classes/com/aayushatharva/brotli4j/decoder/BrotliInputStream.class
cp -a httpclient5/src/main/resources/. build/classes/
grep -F -q 'info.release   = %{version}' \
	build/classes/org/apache/hc/client5/version.properties
test -s build/classes/org/publicsuffix/list/effective_tld_names.dat
cat > build/MANIFEST.MF << 'EOF'
Manifest-Version: 1.0
Implementation-Title: Apache HttpComponents Client
Implementation-Version: %{version}
Implementation-Vendor: The Apache Software Foundation
Automatic-Module-Name: org.apache.httpcomponents.client5.httpclient5
EOF
"$JAVA_HOME/bin/jar" cfm build/httpclient5.jar build/MANIFEST.MF -C build/classes .
test -s build/httpclient5.jar
cat > build/httpclient5.pom << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.apache.httpcomponents.client5</groupId>
  <artifactId>httpclient5</artifactId>
  <version>%{version}</version>
  <name>Apache HttpClient</name>
  <description>Apache HttpComponents Client</description>
  <url>https://hc.apache.org/httpcomponents-client-5.6.x/</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
      <distribution>repo</distribution>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.apache.httpcomponents.core5</groupId>
      <artifactId>httpcore5</artifactId>
      <version>%{httpcorever}</version>
    </dependency>
    <dependency>
      <groupId>org.apache.httpcomponents.core5</groupId>
      <artifactId>httpcore5-h2</artifactId>
      <version>%{httpcorever}</version>
    </dependency>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
      <version>%{slf4jver}</version>
    </dependency>
    <dependency>
      <groupId>org.apache.commons</groupId>
      <artifactId>commons-compress</artifactId>
      <version>%{compressver}</version>
      <optional>true</optional>
    </dependency>
  </dependencies>
</project>
EOF

%install
sysjar install --buildroot %{buildroot} \
	--artifact "build/httpclient5.pom:build/httpclient5.jar" \
	--file-name httpclient5 \
	--filelist .mfiles

%check
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java}"
if "$JAVA_HOME/bin/jar" tf build/httpclient5.jar | grep -E 'org/conscrypt/|com/github/luben/|com/aayushatharva/'; then
	echo "compile-only classes leaked into httpclient5.jar" >&2
	exit 1
fi
"$JAVA_HOME/bin/jar" tf build/httpclient5.jar | grep -F -q org/publicsuffix/list/effective_tld_names.dat
mkdir -p build/vercheck
( cd build/vercheck && "$JAVA_HOME/bin/jar" xf ../httpclient5.jar org/apache/hc/client5/version.properties )
grep -F -q 'info.release   = %{version}' build/vercheck/org/apache/hc/client5/version.properties
grep -F -q 'info.module    = httpclient5' build/vercheck/org/apache/hc/client5/version.properties
cat > HcSmoke.java << 'EOF'
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.psl.PublicSuffixMatcher;
import org.apache.hc.client5.http.psl.PublicSuffixMatcherLoader;
import org.apache.hc.core5.util.VersionInfo;
public class HcSmoke {
    public static void main(String[] args) throws Exception {
        HttpGet get = new HttpGet("http://example.test/a%%20b");
        if (!"/a%%20b".equals(get.getPath())) {
            throw new RuntimeException("path " + get.getPath());
        }
        if (!"GET".equals(get.getMethod())) {
            throw new RuntimeException(get.getMethod());
        }
        VersionInfo vi = VersionInfo.loadVersionInfo("org.apache.hc.client5", HcSmoke.class.getClassLoader());
        if (vi == null || !"%{version}".equals(vi.getRelease()) || !"httpclient5".equals(vi.getModule())) {
            throw new RuntimeException(vi == null ? "null" : vi.getModule() + " " + vi.getRelease());
        }
        PublicSuffixMatcher matcher = PublicSuffixMatcherLoader.getDefault();
        if (matcher == null || !matcher.matches("co.uk") || matcher.matches("example.com") || !matcher.verify("example.com")) {
            throw new RuntimeException("suffix list");
        }
        System.out.println("httpclient5 ok " + vi.getRelease() + " " + get.getPath());
    }
}
EOF
"$JAVA_HOME/bin/javac" --release 8 -proc:none -encoding UTF-8 \
	-cp "build/httpclient5.jar:%{_javadir}/httpcore5.jar:%{_javadir}/httpcore5-h2.jar:%{_javadir}/slf4j/slf4j-api.jar" \
	HcSmoke.java
"$JAVA_HOME/bin/java" -cp "build/httpclient5.jar:%{_javadir}/httpcore5.jar:%{_javadir}/httpcore5-h2.jar:%{_javadir}/slf4j/slf4j-api.jar:." HcSmoke > check.log
grep -F -q 'httpclient5 ok %{version}' check.log
grep -F -q '/a%%20b' check.log
"$JAVA_HOME/bin/jar" --describe-module --file build/httpclient5.jar > check-module.log
grep -F -q 'org.apache.httpcomponents.client5.httpclient5' check-module.log

%files -f .mfiles
%license LICENSE.txt NOTICE.txt
%doc README.md RELEASE_NOTES.txt SECURITY.md
