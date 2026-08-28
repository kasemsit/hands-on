/* โปรแกรมธรรมดาที่ขอหน่วยความจำไปเรื่อย ๆ
   ไม่รู้ตัวเลยว่ากำลังถูกดัก — เหมือน PyTorch ที่ไม่รู้ว่ามี HAMi อยู่ */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);   /* ปิด buffer ให้ลำดับบรรทัดตรงกับ stderr */

    for (int i = 1; i <= 8; i++) {
        void *p = malloc(25 * 1024 * 1024);       /* ขอทีละ 25 MB */
        printf("ขอครั้งที่ %d (25 MB) → %s\n", i, p ? "สำเร็จ" : "OOM");
        if (!p) break;
    }
    return 0;
}
