import csv
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ==========================================================
# CONFIGURATION
# ==========================================================

TARGET_HOTELS = 100

DATE_RANGE = "10 Sep 2026 - 11 Sep 2026"

OUTPUT_FILE = "oyo_hotel_availability.csv"

OYO_URL = (
    "https://www.oyorooms.com/search/"
    "?checkin=10%2F09%2F2026"
    "&checkout=11%2F09%2F2026"
    "&city=Goa"
    "&country=india"
    "&guests=1"
    "&location=Goa%2C%20India"
)

# Number of times to try scrolling when no new hotels appear
MAX_NO_CHANGE = 5

SCROLL_WAIT = 3

HOTEL_PAGE_WAIT = 3


# ==========================================================
# START CHROME
# ==========================================================

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)

wait = WebDriverWait(driver, 20)


# ==========================================================
# HOTEL DATA
# ==========================================================

hotel_data = {}


# ==========================================================
# CHECK LISTING PAGE AVAILABILITY
# ==========================================================

def get_listing_availability(hotel_title):

    try:

        hotels = driver.find_elements(
            By.CSS_SELECTOR,
            "h3.listingHotelDescription__hotelName"
        )

        for hotel in hotels:

            name = hotel.get_attribute("title")

            if not name:
                name = hotel.text.strip()

            if name != hotel_title:
                continue


            # Find parent elements
            ancestors = hotel.find_elements(
                By.XPATH,
                "./ancestor::div"
            )


            # Check ancestors for availability text
            for ancestor in reversed(ancestors):

                try:

                    text = ancestor.text.lower()

                    if "book now" in text:
                        return True

                    if "sold out" in text:
                        return False

                except Exception:
                    continue


        return False


    except Exception as e:

        print(
            f"Listing availability error: {e}"
        )

        return False


# ==========================================================
# CHECK INDIVIDUAL HOTEL PAGE
# ==========================================================

def get_hotel_page_availability(hotel_url):

    original_window = driver.current_window_handle

    try:

        # Open hotel in new tab
        driver.execute_script(
            "window.open(arguments[0], '_blank');",
            hotel_url
        )

        driver.switch_to.window(
            driver.window_handles[-1]
        )


        print("Opening hotel page...")


        # Wait for page
        wait.until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "body")
            )
        )

        time.sleep(HOTEL_PAGE_WAIT)


        # ==================================================
        # CHECK CONTINUE TO BOOK
        # ==================================================

        continue_buttons = driver.find_elements(
            By.XPATH,
            "//button["
            "contains(normalize-space(.), 'Continue to Book')"
            " or "
            ".//*[contains(normalize-space(.), "
            "'Continue to Book')]"
            "]"
        )


        if continue_buttons:

            return True


        # ==================================================
        # CHECK SOLD OUT
        # ==================================================

        sold_out_elements = driver.find_elements(
            By.XPATH,
            "//*[contains("
            "translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),"
            "'sold out'"
            ")]"
        )


        if sold_out_elements:

            return False


        # ==================================================
        # FALLBACK
        # ==================================================

        page_text = driver.find_element(
            By.TAG_NAME,
            "body"
        ).text.lower()


        if "continue to book" in page_text:

            return True


        if "sold out" in page_text:

            return False


        return False


    except Exception as e:

        print(
            f"Hotel page error: {e}"
        )

        return False


    finally:

        # Close hotel tab
        if len(driver.window_handles) > 1:

            driver.close()

            driver.switch_to.window(
                original_window
            )


# ==========================================================
# COLLECT HOTELS
# ==========================================================

def collect_hotels():

    no_change_count = 0


    print()
    print("==============================================")
    print("COLLECTING HOTELS")
    print("==============================================")


    while len(hotel_data) < TARGET_HOTELS:


        # --------------------------------------------------
        # Find currently loaded hotels
        # --------------------------------------------------

        hotels = driver.find_elements(
            By.CSS_SELECTOR,
            "h3.listingHotelDescription__hotelName"
        )


        previous_count = len(hotel_data)


        # --------------------------------------------------
        # Process every currently loaded hotel
        # --------------------------------------------------

        for hotel in hotels:

            try:

                # ==========================================
                # HOTEL NAME
                # ==========================================

                hotel_name = hotel.get_attribute(
                    "title"
                )

                if not hotel_name:

                    hotel_name = hotel.text.strip()


                # ==========================================
                # HOTEL URL
                # ==========================================

                hotel_link = hotel.find_element(
                    By.XPATH,
                    "./ancestor::a[1]"
                )

                hotel_url = hotel_link.get_attribute(
                    "href"
                )


                if not hotel_name or not hotel_url:

                    continue


                # Remove query parameters
                hotel_url = hotel_url.split("?")[0]


                # ==========================================
                # CHECK DUPLICATE
                # ==========================================

                if hotel_url not in hotel_data:


                    # ======================================
                    # LISTING AVAILABILITY
                    # ======================================

                    listing_available = (
                        get_listing_availability(
                            hotel_name
                        )
                    )


                    # ======================================
                    # SAVE HOTEL
                    # ======================================

                    hotel_data[hotel_url] = {

                        "hotel_name":
                            hotel_name,

                        "hotel_url":
                            hotel_url,

                        "isAvailableOnListing":
                            listing_available
                    }


                    print(
                        f"[{len(hotel_data)}/"
                        f"{TARGET_HOTELS}] "
                        f"{hotel_name} | "
                        f"Listing: "
                        f"{listing_available}"
                    )


                # Stop collecting after 100
                if len(hotel_data) >= TARGET_HOTELS:

                    break


            except Exception as e:

                print(
                    f"Error collecting hotel: {e}"
                )

                continue


        # ==================================================
        # CURRENT COUNT
        # ==================================================

        current_count = len(hotel_data)


        print()
        print(
            f"Hotels collected: "
            f"{current_count}/{TARGET_HOTELS}"
        )


        # ==================================================
        # STOP CONDITION 1
        # ==================================================

        if current_count >= TARGET_HOTELS:

            print()
            print(
                "100 hotels collected."
            )

            break


        # ==================================================
        # CHECK WHETHER NEW HOTELS WERE FOUND
        # ==================================================

        if current_count == previous_count:

            no_change_count += 1

            print(
                f"No new hotels found "
                f"({no_change_count}/"
                f"{MAX_NO_CHANGE})"
            )

        else:

            no_change_count = 0


        # ==================================================
        # STOP CONDITION 2
        # ==================================================

        if no_change_count >= MAX_NO_CHANGE:

            print()
            print("----------------------------------------------")
            print("NO MORE HOTELS FOUND")
            print("----------------------------------------------")

            print(
                f"Total hotels collected: "
                f"{current_count}"
            )

            print(
                "Saving all collected hotels..."
            )

            break


        # ==================================================
        # SCROLL
        # ==================================================

        print("Scrolling...")

        driver.execute_script(
            "window.scrollTo("
            "0, document.body.scrollHeight"
            ");"
        )

        time.sleep(SCROLL_WAIT)


    # ======================================================
    # RETURN WHATEVER WAS FOUND
    # ======================================================

    return list(hotel_data.values())


# ==========================================================
# SAVE CSV
# ==========================================================

def save_csv(results):

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        fieldnames = [
            "hotel_name",
            "date_range",
            "isAvailableOnListing",
            "isAvailableOnHotelPage"
        ]


        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )


        writer.writeheader()

        writer.writerows(results)


    print()
    print("----------------------------------------------")
    print("CSV SAVED")
    print("----------------------------------------------")

    print(
        f"File: {OUTPUT_FILE}"
    )

    print(
        f"Entries: {len(results)}"
    )


# ==========================================================
# MAIN PROGRAM
# ==========================================================

try:

    # ======================================================
    # OPEN OYO
    # ======================================================

    print()
    print("==============================================")
    print("OYO AUTOMATED QA TEST")
    print("==============================================")


    print(
        "Opening OYO Goa search page..."
    )


    driver.get(OYO_URL)


    # ======================================================
    # WAIT FOR HOTELS
    # ======================================================

    wait.until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "h3.listingHotelDescription__hotelName"
            )
        )
    )


    time.sleep(3)


    # ======================================================
    # COLLECT HOTELS
    # ======================================================

    hotels = collect_hotels()


    # ======================================================
    # SHOW COLLECTION RESULT
    # ======================================================

    print()
    print("==============================================")
    print("COLLECTION FINISHED")
    print("==============================================")


    print(
        f"Hotels found: "
        f"{len(hotels)}"
    )


    if len(hotels) < TARGET_HOTELS:

        print(
            f"Only {len(hotels)} unique hotels "
            f"were available."
        )

        print(
            f"Target was {TARGET_HOTELS}."
        )

        print(
            "Continuing with all available hotels."
        )


    else:

        print(
            "100 hotels successfully collected."
        )


    # ======================================================
    # TEST INDIVIDUAL HOTEL PAGES
    # ======================================================

    results = []


    for index, hotel in enumerate(
        hotels,
        start=1
    ):


        hotel_name = hotel["hotel_name"]

        hotel_url = hotel["hotel_url"]

        listing_available = (
            hotel["isAvailableOnListing"]
        )


        print()
        print("==============================================")
        print(
            f"TESTING HOTEL "
            f"{index}/{len(hotels)}"
        )
        print("==============================================")


        print(
            f"Hotel: {hotel_name}"
        )


        print(
            f"Listing: "
            f"{listing_available}"
        )


        # ==================================================
        # HOTEL PAGE CHECK
        # ==================================================

        hotel_page_available = (
            get_hotel_page_availability(
                hotel_url
            )
        )


        print(
            f"Hotel Page: "
            f"{hotel_page_available}"
        )


        # ==================================================
        # ADD RESULT
        # ==================================================

        results.append({

            "hotel_name":
                hotel_name,

            "date_range":
                DATE_RANGE,

            "isAvailableOnListing":
                listing_available,

            "isAvailableOnHotelPage":
                hotel_page_available
        })


    # ======================================================
    # SAVE WHATEVER NUMBER OF RESULTS WE HAVE
    # ======================================================

    save_csv(results)


    # ======================================================
    # FINAL MESSAGE
    # ======================================================

    print()
    print()
    print("==============================================")
    print("           SCRAPING COMPLETED")
    print("==============================================")


    print(
        f"Total entries saved: "
        f"{len(results)}"
    )


    print(
        f"CSV file: "
        f"{OUTPUT_FILE}"
    )


    print("==============================================")


finally:

    driver.quit()

    print()
    print("Browser closed.")