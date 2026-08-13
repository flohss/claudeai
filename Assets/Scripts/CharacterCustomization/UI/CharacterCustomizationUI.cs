using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace CharacterCustomization.UI
{
    /// <summary>
    /// Reference wiring showing how a UI layer binds to CharacterCustomizationManager.
    /// Builds one slider per MorphSlider entry so adding sliders never requires touching
    /// this script — only the MorphProfile asset.
    /// </summary>
    public class CharacterCustomizationUI : MonoBehaviour
    {
        [SerializeField] private CharacterCustomizationManager manager;
        [SerializeField] private Transform bodySliderContainer;
        [SerializeField] private Transform faceSliderContainer;
        [SerializeField] private Slider sliderPrefab;
        [SerializeField] private Image skinColorSwatch;

        private void Start()
        {
            BuildSliders(MorphCategory.Body, bodySliderContainer);
            BuildSliders(MorphCategory.Face, faceSliderContainer);
        }

        private void BuildSliders(MorphCategory category, Transform container)
        {
            if (container == null || sliderPrefab == null)
            {
                return;
            }

            foreach (var slider in manager.Morphs.Profile.sliders)
            {
                if (slider.category != category)
                {
                    continue;
                }

                var uiSlider = Instantiate(sliderPrefab, container);
                uiSlider.minValue = 0f;
                uiSlider.maxValue = 100f;
                uiSlider.value = manager.Morphs.GetValue(slider.id);

                var sliderId = slider.id;
                uiSlider.onValueChanged.AddListener(value => manager.Morphs.SetValue(sliderId, value));

                var label = uiSlider.GetComponentInChildren<TMP_Text>();
                if (label != null)
                {
                    label.text = slider.displayName;
                }
            }
        }

        public void OnSkinColorChanged(Color color)
        {
            manager.Appearance.SetSkinColor(color);

            if (skinColorSwatch != null)
            {
                skinColorSwatch.color = color;
            }
        }

        public void OnHairSelected(string hairId, Color color)
        {
            manager.Appearance.SetHair(hairId, color);
        }

        public void OnEquip(string clothingItemId)
        {
            var item = manager.FindClothing(clothingItemId);
            if (item != null)
            {
                manager.Equipment.Equip(item);
            }
        }

        public void OnUnequip(EquipmentSlot slot)
        {
            manager.Equipment.Unequip(slot);
        }
    }
}
