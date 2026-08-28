/* โจทย์ฝึกแกะโปรแกรม — บทที่ 63
   คอมไพล์: gcc -O0 -no-pie -o crackme crackme.c            */
#include <stdio.h>
#include <string.h>

int check(const char *pw) {
    return strcmp(pw, "s3cr3t") == 0;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        printf("ใช้: %s <รหัสผ่าน>\n", argv[0]);
        return 2;
    }
    if (check(argv[1])) {
        printf("ผ่าน\n");
        return 0;
    }
    printf("ไม่ผ่าน\n");
    return 1;
}
